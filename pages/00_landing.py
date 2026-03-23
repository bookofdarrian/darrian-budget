"""
Peach State Savings — Poetic Launch Landing Page
Inspired by:
  - Pusha T, "Gold Rings" (the specific verse on earning, stacking, sovereign wealth)
  - J. Cole, "03 Adolescence" (first-gen ambition, figuring it out alone)
  - Mavi, "Mike" (quiet dignity, internal currency, doing it for the culture)

No login required. Shown to all visitors before they authenticate.
"""

import streamlit as st
import base64
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.carousel import (
    CAROUSEL_BASE_CSS,
    carousel_theme_css,
)

_BASE = Path(__file__).parent.parent


def _load_b64(path: str, mime: str = "image/jpeg") -> str:
    try:
        p = Path(path) if Path(path).is_absolute() else _BASE / path
        with open(p, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{data}"
    except Exception:
        return ""


_HEADSHOT     = _load_b64("static/photos/darrian_headshot.png", "image/png")
_HERO_IMG_SRC = _load_b64("static/dashboard_screenshot.png", "image/png")

st.set_page_config(
    page_title="Peach State Savings — Build Like You Already Won",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Color System ─────────────────────────────────────────────────────────────
PEACH       = "#CC5500"
PEACH_LIGHT = "#E8681A"
PEACH_DARK  = "#8B3800"
PEACH_GLOW  = "rgba(204,85,0,0.10)"
BG_MAIN     = "#080808"
BG_SURFACE  = "#111111"
BG_CARD     = "#181818"
BG_BORDER   = "#2A2A2A"
TEXT_MAIN   = "#F0EBE3"
TEXT_MUTED  = "#857E76"
TEXT_DIM    = "#3A3530"
SUCCESS     = "#22C55E"
GOLD        = "#C9A84C"   # Pusha's gold — earned, not given
VERSE_COLOR = "#D4C5A9"   # aged paper, manuscript warmth

# ── SEO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<script>
(function() {
  var metas = [
    { name: 'description', content: 'Peach State Savings — free AI-powered personal finance. Import bank statements, track RSUs, build wealth. Private, self-hosted, built in Atlanta.' },
    { property: 'og:title', content: 'Peach State Savings — Build Like You Already Won' },
    { property: 'og:description', content: 'Free AI budgeting, bank import, RSU tracker, 73+ tools. Self-hosted. Atlanta-built.' },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: 'https://peachstatesavings.com' },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'robots', content: 'index, follow' },
    { name: 'keywords', content: 'personal finance app free, AI budgeting, bank statement import, RSU tracker, net worth, self hosted finance app, Atlanta' },
    { name: 'author', content: 'Darrian Belcher' },
    { name: 'theme-color', content: '#CC5500' }
  ];
  metas.forEach(function(attrs) {
    var existing = attrs.name
      ? document.querySelector('meta[name="'+attrs.name+'"]')
      : document.querySelector('meta[property="'+attrs.property+'"]');
    var tag = existing || document.createElement('meta');
    Object.keys(attrs).forEach(function(k){ tag.setAttribute(k, attrs[k]); });
    if (!existing) document.head.appendChild(tag);
  });
  if (!document.querySelector('link[rel="canonical"]')) {
    var link = document.createElement('link');
    link.rel = 'canonical'; link.href = 'https://peachstatesavings.com';
    document.head.appendChild(link);
  }
})();
</script>

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Peach State Savings",
  "url": "https://peachstatesavings.com",
  "description": "Free AI-powered personal finance app with 73+ tools. Self-hosted in Atlanta, GA.",
  "applicationCategory": "FinanceApplication",
  "operatingSystem": "Web",
  "offers": [
    { "@type": "Offer", "name": "Free", "price": "0", "priceCurrency": "USD" },
    { "@type": "Offer", "name": "Pro", "price": "4.99", "priceCurrency": "USD", "billingDuration": "P1M" }
  ],
  "author": {
    "@type": "Person",
    "name": "Darrian Belcher",
    "url": "https://www.linkedin.com/in/darrian-belcher/"
  }
}
</script>
""", unsafe_allow_html=True)

# ── Master CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;500;600;700&family=EB+Garamond:ital,wght@0,400;0,500;1,400;1,500&display=swap');

:root {{
  --peach: {PEACH};
  --peach-light: {PEACH_LIGHT};
  --peach-dark: {PEACH_DARK};
  --peach-glow: {PEACH_GLOW};
  --bg-main: {BG_MAIN};
  --bg-surface: {BG_SURFACE};
  --bg-card: {BG_CARD};
  --bg-border: {BG_BORDER};
  --text-main: {TEXT_MAIN};
  --text-muted: {TEXT_MUTED};
  --text-dim: {TEXT_DIM};
  --success: {SUCCESS};
  --gold: {GOLD};
  --verse: {VERSE_COLOR};
  --radius-sm: 2px;
  --radius-md: 3px;
  --radius-lg: 4px;
  --transition: 0.18s ease;
  --font-display: 'Oswald', 'Arial Narrow', Arial, sans-serif;
  --font-verse: 'EB Garamond', Georgia, 'Times New Roman', serif;
  --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

*, *::before, *::after {{ box-sizing: border-box; }}
.main .block-container {{
  max-width: 1100px;
  padding: 0 1.5rem 6rem 1.5rem;
  margin: 0 auto;
}}
body, .stApp {{ background: var(--bg-main); color: var(--text-main); font-family: var(--font-body); }}
.stApp {{ background: var(--bg-main) !important; }}

/* grain */
.stApp::after {{
  content: '';
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");
  opacity: 0.022;
  pointer-events: none;
  z-index: 9999;
}}

h1, h2, h3, .stat-num, .hero-h1, .section-h2, .how-num {{
  font-family: var(--font-display) !important;
}}

#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stSidebarNav"], [data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}

/* ── TOP NAV ── */
.top-nav {{
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(8,8,8,0.96);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--bg-border);
  padding: 14px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}}
.nav-brand {{
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--peach);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-decoration: none;
}}
.nav-links {{
  display: flex;
  gap: 28px;
  align-items: center;
}}
.nav-link {{
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 500;
  text-decoration: none;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  transition: color var(--transition);
}}
.nav-link:hover {{ color: var(--text-main); }}

/* ── VERSE BLOCK — the poetic anchor ── */
.verse-block {{
  border-left: 3px solid var(--gold);
  padding: 24px 32px;
  margin: 40px 0;
  background: linear-gradient(135deg, rgba(201,168,76,0.04) 0%, transparent 70%);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  position: relative;
}}
.verse-block::before {{
  content: '"';
  position: absolute;
  top: -8px;
  left: 20px;
  font-family: var(--font-verse);
  font-size: 5rem;
  color: var(--gold);
  opacity: 0.18;
  line-height: 1;
  pointer-events: none;
}}
.verse-text {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: clamp(1rem, 1.8vw, 1.25rem);
  color: var(--verse);
  line-height: 1.85;
  letter-spacing: 0.01em;
}}
.verse-text em {{
  font-style: normal;
  color: var(--gold);
  font-weight: 500;
}}
.verse-attr {{
  margin-top: 16px;
  font-size: 0.78rem;
  color: var(--text-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: var(--font-display);
}}

/* ── HERO ── */
.hero {{
  text-align: center;
  padding: 80px 20px 56px;
  position: relative;
}}
.hero-eyebrow {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--peach-glow);
  border: 1px solid rgba(204,85,0,0.3);
  color: var(--peach-light);
  font-family: var(--font-display);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 6px 18px;
  border-radius: 100px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 32px;
}}
.hero-h1 {{
  font-size: clamp(2.4rem, 5.5vw, 4.2rem);
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.05;
  letter-spacing: -0.02em;
  margin-bottom: 0;
  text-transform: uppercase;
}}
.hero-h1 .gold-line {{
  display: block;
  background: linear-gradient(90deg, var(--gold), var(--peach-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.hero-h1 .peach-line {{
  display: block;
  background: linear-gradient(90deg, var(--peach), var(--peach-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.hero-drop {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: clamp(1rem, 1.8vw, 1.2rem);
  color: var(--text-muted);
  max-width: 580px;
  margin: 28px auto 44px;
  line-height: 1.85;
}}
.hero-drop em {{
  font-style: normal;
  color: var(--verse);
}}
.hero-trust {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  flex-wrap: wrap;
  margin-top: 14px;
}}
.trust-item {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-muted);
  font-family: var(--font-display);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
.trust-check {{ color: var(--success); font-size: 0.9rem; }}

/* ── STATS BAR ── */
.stats-bar {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--bg-border);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin: 52px 0;
}}
.stat-item {{
  background: var(--bg-surface);
  padding: 28px 16px;
  text-align: center;
}}
.stat-num {{
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--peach);
  line-height: 1;
  letter-spacing: -0.02em;
}}
.stat-label {{
  font-family: var(--font-display);
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 8px;
}}

/* ── SECTION ── */
.section {{ margin: 80px 0; }}
.section-eyebrow {{
  font-family: var(--font-display);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--peach);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  text-align: center;
  margin-bottom: 14px;
}}
.section-h2 {{
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  font-weight: 700;
  color: var(--text-main);
  text-align: center;
  letter-spacing: -0.02em;
  line-height: 1.1;
  margin-bottom: 14px;
  text-transform: uppercase;
}}
.section-sub {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: 1.05rem;
  color: var(--text-muted);
  text-align: center;
  max-width: 520px;
  margin: 0 auto 52px;
  line-height: 1.75;
}}

/* ── MANIFESTO STRIP ── */
.manifesto {{
  background: linear-gradient(160deg, rgba(201,168,76,0.06) 0%, rgba(8,8,8,0) 50%);
  border: 1px solid rgba(201,168,76,0.2);
  border-radius: 4px;
  padding: 52px 48px;
  margin: 64px 0;
  position: relative;
  overflow: hidden;
}}
.manifesto::after {{
  content: 'GOLD RINGS';
  position: absolute;
  bottom: -16px;
  right: 24px;
  font-family: var(--font-display);
  font-size: 5rem;
  font-weight: 700;
  color: var(--gold);
  opacity: 0.04;
  letter-spacing: 0.15em;
  pointer-events: none;
  user-select: none;
}}
.manifesto-line {{
  font-family: var(--font-display);
  font-size: clamp(1.2rem, 2.2vw, 1.7rem);
  font-weight: 500;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  line-height: 1.4;
  margin-bottom: 12px;
}}
.manifesto-line span.accent {{
  color: var(--gold);
}}
.manifesto-line span.peach {{
  color: var(--peach-light);
}}

/* ── FEATURE CARDS ── */
.feat-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 14px;
}}
.feat-card {{
  background: var(--bg-card);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 26px 22px;
  transition: border-color var(--transition), transform var(--transition);
}}
.feat-card:hover {{
  border-color: var(--peach);
  transform: translateY(-2px);
}}
.feat-icon {{
  font-size: 1.7rem;
  margin-bottom: 12px;
  display: block;
}}
.feat-title {{
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 10px;
}}
.feat-desc {{
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.65;
}}

/* ── HOW IT WORKS ── */
.how-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 28px;
}}
.how-step {{
  text-align: center;
  padding: 36px 24px;
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  position: relative;
}}
.how-num {{
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--peach-glow);
  border: 2px solid var(--peach);
  color: var(--peach);
  font-size: 1.3rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 18px;
}}
.how-title {{
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 10px;
}}
.how-desc {{
  font-size: 0.87rem;
  color: var(--text-muted);
  line-height: 1.65;
}}

/* ── BUILDER ── */
.builder-card {{
  background: linear-gradient(135deg, rgba(201,168,76,0.07) 0%, var(--bg-card) 100%);
  border: 1px solid rgba(201,168,76,0.22);
  border-radius: 4px;
  padding: 52px 48px;
}}
.builder-header {{
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 28px;
}}
.builder-name {{
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
.builder-role {{
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 3px;
}}
.builder-verse {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: 1.1rem;
  color: var(--verse);
  line-height: 1.9;
  border-left: 3px solid var(--gold);
  padding-left: 22px;
  margin: 24px 0;
}}
.builder-body {{
  color: #C0BDB8;
  font-size: 0.93rem;
  line-height: 1.9;
}}

/* ── TESTIMONIALS ── */
.testimonial-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}}
.testimonial-card {{
  background: var(--bg-card);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 26px;
}}
.testimonial-stars {{
  color: var(--gold);
  font-size: 0.9rem;
  margin-bottom: 14px;
  letter-spacing: 2px;
}}
.testimonial-text {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: 0.92rem;
  color: var(--text-main);
  line-height: 1.75;
  margin-bottom: 18px;
}}
.testimonial-author {{
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--peach-light);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
.testimonial-role {{
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 3px;
}}

/* ── PRICING ── */
.pricing-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  max-width: 660px;
  margin: 0 auto;
}}
.price-card {{
  background: var(--bg-card);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 34px 28px;
  position: relative;
}}
.price-card.featured {{
  border-color: var(--peach);
  background: linear-gradient(135deg, rgba(204,85,0,0.07) 0%, var(--bg-card) 100%);
}}
.price-badge {{
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--peach);
  color: #000;
  font-family: var(--font-display);
  font-size: 0.68rem;
  font-weight: 700;
  padding: 4px 14px;
  border-radius: 100px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}}
.price-name {{
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 14px;
}}
.price-num {{
  font-family: var(--font-display);
  font-size: 3rem;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1;
  letter-spacing: -0.03em;
}}
.price-dollar {{
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-muted);
  vertical-align: super;
}}
.price-period {{
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 24px;
}}
.price-divider {{
  border: none;
  border-top: 1px solid var(--bg-border);
  margin: 20px 0;
}}
.price-feature {{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.86rem;
  color: #B8C0D0;
  margin: 9px 0;
  line-height: 1.45;
}}
.price-check {{ color: var(--peach); font-weight: 700; flex-shrink: 0; }}

/* ── BIZ CARDS ── */
.biz-section {{
  background: linear-gradient(160deg, rgba(201,168,76,0.05) 0%, rgba(8,8,8,0) 55%);
  border: 1px solid rgba(201,168,76,0.18);
  border-radius: 4px;
  padding: 56px 48px;
  margin-top: 16px;
}}
.biz-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 40px;
}}
.biz-card {{
  background: var(--bg-card);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 32px 26px;
  display: flex;
  flex-direction: column;
  transition: border-color var(--transition), transform var(--transition);
}}
.biz-card:hover {{
  border-color: var(--gold);
  transform: translateY(-3px);
}}
.biz-card.highlight {{
  border-color: rgba(201,168,76,0.4);
  background: linear-gradient(135deg, rgba(201,168,76,0.06) 0%, var(--bg-card) 100%);
}}
.biz-badge {{
  display: inline-block;
  background: linear-gradient(135deg, var(--gold), #8B6B20);
  color: #000;
  font-family: var(--font-display);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 4px 12px;
  border-radius: 100px;
  margin-bottom: 16px;
  width: fit-content;
}}
.biz-icon {{ font-size: 2rem; margin-bottom: 12px; display: block; }}
.biz-name {{
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}}
.biz-price {{
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--gold);
  letter-spacing: -0.03em;
  line-height: 1;
  margin-bottom: 4px;
}}
.biz-price-sub {{ font-size: 0.78rem; color: var(--text-muted); margin-bottom: 16px; }}
.biz-desc {{ font-size: 0.86rem; color: var(--text-muted); line-height: 1.65; margin-bottom: 18px; flex: 1; }}
.biz-feature {{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.83rem;
  color: #B0B8CA;
  margin-bottom: 8px;
  line-height: 1.45;
}}
.biz-check {{ color: var(--success); font-weight: 900; flex-shrink: 0; margin-top: 1px; }}
.biz-divider {{ border: none; border-top: 1px solid var(--bg-border); margin: 16px 0; }}
.biz-cta-note {{
  margin-top: 18px;
  font-size: 0.76rem;
  color: var(--text-dim);
  font-style: italic;
  text-align: center;
}}

/* ── FAQ ── */
.faq-item {{
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 22px 26px;
  margin-bottom: 12px;
  background: var(--bg-card);
  transition: border-color var(--transition);
}}
.faq-item:hover {{ border-color: rgba(201,168,76,0.28); }}
.faq-q {{
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 10px;
}}
.faq-a {{
  font-size: 0.88rem;
  color: var(--text-muted);
  line-height: 1.72;
}}

/* ── CTA ── */
.cta-section {{
  background: linear-gradient(135deg, rgba(201,168,76,0.08) 0%, rgba(204,85,0,0.05) 50%, rgba(8,8,8,0) 100%);
  border: 1px solid rgba(201,168,76,0.2);
  border-radius: 4px;
  padding: 76px 40px;
  text-align: center;
  position: relative;
  overflow: hidden;
}}
.cta-section::before {{
  content: '';
  position: absolute;
  top: -80px; left: 50%;
  transform: translateX(-50%);
  width: 600px; height: 320px;
  background: radial-gradient(ellipse, rgba(201,168,76,0.1) 0%, transparent 70%);
  pointer-events: none;
}}
.cta-h2 {{
  font-size: clamp(1.8rem, 3.5vw, 2.8rem);
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: -0.01em;
  line-height: 1.1;
  margin-bottom: 16px;
}}
.cta-h2 .gold-word {{ color: var(--gold); }}
.cta-verse {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: 1.1rem;
  color: var(--verse);
  max-width: 520px;
  margin: 0 auto 40px;
  line-height: 1.85;
}}

/* ── FOOTER ── */
.site-footer {{
  border-top: 1px solid var(--bg-border);
  padding: 44px 0 28px;
  margin-top: 88px;
}}
.footer-grid {{
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 44px;
  margin-bottom: 36px;
}}
.footer-brand {{
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  color: var(--peach);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}}
.footer-tagline {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: 0.87rem;
  color: var(--text-muted);
  line-height: 1.7;
  max-width: 300px;
}}
.footer-col-title {{
  font-family: var(--font-display);
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 14px;
}}
.footer-link {{
  display: block;
  font-size: 0.84rem;
  color: var(--text-muted);
  text-decoration: none;
  margin-bottom: 9px;
  transition: color var(--transition);
}}
.footer-link:hover {{ color: var(--peach-light); }}
.footer-bottom {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 22px;
  border-top: 1px solid var(--bg-border);
  font-size: 0.78rem;
  color: var(--text-dim);
  flex-wrap: wrap;
  gap: 8px;
}}
.footer-bottom a {{ color: var(--peach); text-decoration: none; }}
.footer-end-verse {{
  font-family: var(--font-verse);
  font-style: italic;
  font-size: 0.82rem;
  color: rgba(201,168,76,0.5);
  text-align: center;
  margin-top: 28px;
  letter-spacing: 0.02em;
}}

/* ── MOCKUP ── */
.hero-mockup {{
  margin: 44px auto 0;
  max-width: 880px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(201,168,76,0.2);
  box-shadow: 0 36px 90px rgba(0,0,0,0.65), 0 0 80px rgba(201,168,76,0.06);
}}
.hero-mockup-bar {{
  background: #0F1010;
  height: 32px;
  border-bottom: 1px solid rgba(201,168,76,0.12);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 7px;
}}
.hero-mockup-dot {{
  width: 12px; height: 12px;
  border-radius: 50%;
  display: inline-block;
}}
.hero-mockup img {{ width: 100%; display: block; }}

/* ── BUTTONS ── */
.stButton > button[kind="primary"] {{
  background: #CC5500 !important;
  color: #F0EBE3 !important;
  border: none !important;
  font-family: var(--font-display) !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
  padding: 14px 32px !important;
  border-radius: var(--radius-sm) !important;
  min-height: 52px !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  box-shadow: none !important;
  transition: background var(--transition) !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: #E06010 !important;
  box-shadow: 0 0 24px rgba(201,168,76,0.15) !important;
}}
.stButton > button:not([kind="primary"]) {{
  background: transparent !important;
  border: 1px solid var(--bg-border) !important;
  color: var(--text-muted) !important;
  font-family: var(--font-display) !important;
  font-size: 0.82rem !important;
  padding: 11px 24px !important;
  border-radius: var(--radius-sm) !important;
  min-height: 44px !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  transition: all var(--transition) !important;
}}
.stButton > button:not([kind="primary"]):hover {{
  border-color: var(--gold) !important;
  color: var(--text-main) !important;
}}

/* ── RESPONSIVE ── */
@media (max-width: 768px) {{
  .main .block-container {{ padding: 0 1rem 4rem; }}
  .hero {{ padding: 56px 12px 44px; }}
  .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
  .feat-grid {{ grid-template-columns: 1fr; }}
  .how-grid {{ grid-template-columns: 1fr; }}
  .testimonial-grid {{ grid-template-columns: 1fr; }}
  .pricing-grid {{ grid-template-columns: 1fr; }}
  .biz-grid {{ grid-template-columns: 1fr; }}
  .builder-card, .biz-section {{ padding: 32px 22px; }}
  .cta-section {{ padding: 52px 20px; }}
  .footer-grid {{ grid-template-columns: 1fr; gap: 24px; }}
  .footer-bottom {{ flex-direction: column; text-align: center; }}
  .top-nav .nav-links {{ display: none; }}
  .verse-block {{ padding: 18px 22px; }}
  .manifesto {{ padding: 36px 22px; }}
}}
@media (max-width: 480px) {{
  .stats-bar {{ grid-template-columns: 1fr 1fr; }}
  .hero-h1 {{ font-size: 2rem; }}
  .section-h2 {{ font-size: 1.6rem; }}
}}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TOP NAV
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="top-nav" role="navigation" aria-label="Main navigation">
  <a class="nav-brand" href="/" aria-label="Peach State Savings">🍑 Peach State Savings</a>
  <div class="nav-links">
    <a class="nav-link" href="#features">Features</a>
    <a class="nav-link" href="#how-it-works">How It Works</a>
    <a class="nav-link" href="#pricing">Pricing</a>
    <a class="nav-link" href="#for-business">For Business</a>
    <a class="nav-link" href="#faq">FAQ</a>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# OPENING VERSE — J. Cole "03 Adolescence"
# The spirit: figuring it out alone, first-gen, the weight of being the one who
# has to understand money before anyone taught you how.
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="verse-block" style="max-width:680px; margin:40px auto 0;">
  <div class="verse-text">
    Nobody taught us how to count it.<br>
    Nobody showed us where to put it.<br>
    We learned by losing some, then learned to <em>move different</em> —<br>
    quiet, careful, sovereign.
  </div>
  <div class="verse-attr">echoes of 03 Adolescence · J. Cole · Friday Night Lights</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
_AVATAR_HTML = (
    f'<img src="{_HEADSHOT}" alt="Darrian Belcher" '
    'style="width:40px;height:40px;border-radius:50%;object-fit:cover;'
    'border:2px solid rgba(201,168,76,0.5);flex-shrink:0;" />'
) if _HEADSHOT else ""

st.markdown(f"""
<div class="hero" role="banner">
  <div class="hero-eyebrow" style="gap:10px;">
    {_AVATAR_HTML}
    <span>Built in Atlanta · 73+ Tools · Claude AI · Self-Hosted</span>
  </div>

  <h1 class="hero-h1">
    <span>Know Where</span>
    <span class="gold-line">Every Dollar</span>
    <span class="peach-line">Goes.</span>
  </h1>

  <p class="hero-drop">
    The finance app built for people who <em>figured it out alone</em> —<br>
    first-gen earners, tech workers stacking equity,<br>
    builders who never had a $400/hour advisor,<br>
    and never needed one.
  </p>
</div>
""", unsafe_allow_html=True)

# CTA buttons
hero_l, hero_c, hero_r = st.columns([1, 2, 1])
with hero_c:
    if st.button("🍑  Get Started Free — No Credit Card", type="primary", use_container_width=True, key="hero_cta"):
        st.switch_page("app.py")
    st.markdown("""
    <div class="hero-trust">
      <span class="trust-item"><span class="trust-check">✓</span> Free Forever</span>
      <span class="trust-item"><span class="trust-check">✓</span> Private & Self-Hosted</span>
      <span class="trust-item"><span class="trust-check">✓</span> No Ads</span>
      <span class="trust-item"><span class="trust-check">✓</span> No Data Selling</span>
    </div>
    """, unsafe_allow_html=True)

# Hero screenshot mockup
_HERO_IMG = _load_b64("static/dashboard_screenshot.png", "image/png")
if _HERO_IMG:
    st.markdown(
        f'''<div class="hero-mockup">
  <div class="hero-mockup-bar">
    <span class="hero-mockup-dot" style="background:#ff5f57;"></span>
    <span class="hero-mockup-dot" style="background:#febc2e;"></span>
    <span class="hero-mockup-dot" style="background:#28c840;"></span>
  </div>
  <img src="{_HERO_IMG}" alt="Peach State Savings Dashboard" loading="lazy" />
</div>''',
        unsafe_allow_html=True,
    )

st.markdown(CAROUSEL_BASE_CSS + carousel_theme_css("peach"), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# STATS BAR
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="stats-bar" role="region" aria-label="Key statistics">
  <div class="stat-item">
    <div class="stat-num">73+</div>
    <div class="stat-label">Finance Tools</div>
  </div>
  <div class="stat-item">
    <div class="stat-num">Claude</div>
    <div class="stat-label">AI-Powered</div>
  </div>
  <div class="stat-item">
    <div class="stat-num">100%</div>
    <div class="stat-label">Private & Self-Hosted</div>
  </div>
  <div class="stat-item">
    <div class="stat-num">$0</div>
    <div class="stat-label">To Start</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFESTO — Pusha T "Gold Rings"
# The verse spirit: the grind is the proof, the stacking IS the statement,
# sovereign wealth built in silence, not for clout — for freedom.
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="manifesto">
  <div class="manifesto-line">
    Your money should work <span class="accent">like you do</span>.
  </div>
  <div class="manifesto-line">
    Relentless. <span class="peach">Precise.</span> No days off.
  </div>
  <div class="manifesto-line">
    <span class="accent">Gold rings</span> aren't worn — they're <em>earned</em>.
  </div>
  <div class="manifesto-line">
    Stack the knowledge. <span class="peach">Stack the data.</span>
  </div>
  <div class="manifesto-line">
    Then let the <span class="accent">numbers</span> speak for themselves.
  </div>

  <div class="verse-block" style="margin-top:36px;">
    <div class="verse-text">
      I don't wear my wealth — <em>I track it</em>.<br>
      Every vest, every import, every line in the ledger<br>
      is another brick in something nobody can take.<br>
      That's what Pusha meant. That's what this app is.
    </div>
    <div class="verse-attr">in the spirit of Gold Rings · Pusha T · My Name Is My Name</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="section" id="features">
  <div class="section-eyebrow">Features</div>
  <h2 class="section-h2">Everything Your Finances Need</h2>
  <p class="section-sub">From the daily transaction to the long-term wealth — all the tools serious money managers use.</p>
</div>
""", unsafe_allow_html=True)

features = [
    ("📊", "AI Budget Dashboard", "Track income vs spending in real time. Claude auto-categorizes every transaction and flags unusual patterns before they become problems."),
    ("🏦", "Bank Statement Import", "Paste your bank CSV. Watch it auto-categorize in seconds. Works with NFCU, Chase, BofA, Wells Fargo, and most major US banks."),
    ("🤖", "AI Spending Insights", "Personalized recommendations from Claude — where to cut, where to invest, how to accelerate your goals."),
    ("📈", "RSU & ESPP Tracker", "Built for tech employees. Tracks vest schedules, ESPP periods, tax lots, and net gain after taxes and fees."),
    ("💎", "Net Worth Tracker", "Month-over-month growth charts, asset allocation breakdowns, and AI-powered projections for your financial future."),
    ("🎯", "Financial Goals", "Set goals with deadlines. See progress bars and AI milestone predictions that adjust to your real spending."),
    ("🏠", "Rent vs Buy Calculator", "Full amortization, equity build, opportunity cost, and break-even analysis for your market."),
    ("📋", "Bill Calendar", "Never miss a bill again. Visual calendar, due-date alerts, autopay tracking, monthly cash flow totals."),
    ("💸", "Paycheck Allocator", "Enter gross salary. Get exact net paycheck with federal, GA state taxes, and benefits deductions."),
    ("🧾", "HSA Receipt Vault", "AI-categorized HSA receipts for stress-free tax time. Never lose a qualifying receipt again."),
    ("📉", "Debt Payoff Planner", "Avalanche vs snowball — model your exact payoff date and total interest saved with real charts."),
]

rows = [features[i:i+3] for i in range(0, len(features), 3)]
for row in rows:
    cols = st.columns(len(row), gap="medium")
    for col, (icon, title, desc) in zip(cols, row):
        with col:
            st.markdown(f"""
            <div class="feat-card">
              <span class="feat-icon" role="img" aria-label="{title}">{icon}</span>
              <h3 class="feat-title">{title}</h3>
              <p class="feat-desc">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# INTERLUDE VERSE — Mavi "Mike"
# The spirit: internal wealth, quiet dignity, the kind of richness that isn't
# clout — it's clarity. Knowing your number. Owning your data. Being the Mike
# in your own story.
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="verse-block" style="max-width:700px; margin:64px auto;">
  <div class="verse-text">
    There is a kind of wealth that doesn't announce itself.<br>
    It lives in the spreadsheet no one else can see.<br>
    It lives in knowing your <em>real number</em> — not the one you perform,<br>
    but the one that keeps you free.<br><br>
    That's the Mike in all of us.<br>
    The one who builds in silence<br>
    and wakes up sovereign.
  </div>
  <div class="verse-attr">in the spirit of Mike · Mavi · flexin &amp; crying</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HOW IT WORKS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="section" id="how-it-works">
  <div class="section-eyebrow">How It Works</div>
  <h2 class="section-h2">Full Financial Picture In Under 5 Minutes</h2>
  <p class="section-sub">
    No bank linking. No Open Banking. No giving us your credentials.<br>
    Your data. Your server. Your sovereignty.
  </p>
  <div class="how-grid">
    <div class="how-step">
      <div class="how-num">1</div>
      <h3 class="how-title">Create Your Free Account</h3>
      <p class="how-desc">Email and password. That's it. No credit card, no phone number, no social login. Your account is private and lives on a self-hosted server in Atlanta.</p>
    </div>
    <div class="how-step">
      <div class="how-num">2</div>
      <h3 class="how-title">Import Your Bank Statement</h3>
      <p class="how-desc">Export CSV from NFCU, Chase, BofA — paste it in. Claude AI auto-categorizes every transaction in seconds. No manual tagging. No waiting.</p>
    </div>
    <div class="how-step">
      <div class="how-num">3</div>
      <h3 class="how-title">See the Full Picture</h3>
      <p class="how-desc">Budget, net worth, goals, AI insights — live immediately. Upgrade to Pro for RSU tracking, portfolio analytics, and all 73+ advanced tools.</p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTIMONIALS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="section">
  <div class="section-eyebrow">Real People. Real Money.</div>
  <h2 class="section-h2">They Built Different</h2>
  <p class="section-sub">Peach State Savings users have paid off debt, hit savings goals, and finally understood their RSU compensation.</p>
  <div class="testimonial-grid">
    <div class="testimonial-card">
      <div class="testimonial-stars">★★★★★</div>
      <p class="testimonial-text">"I finally understand my Visa RSU vests and ESPP. The tax breakdown alone saved me from a surprise IRS bill. This is the finance app I wish existed 3 years ago."</p>
      <div class="testimonial-author">Marcus T.</div>
      <div class="testimonial-role">Software Engineer · Atlanta, GA</div>
    </div>
    <div class="testimonial-card">
      <div class="testimonial-stars">★★★★★</div>
      <p class="testimonial-text">"I paste my NFCU statement and every transaction is categorized perfectly. I went from not knowing my spending to being fully on budget in a week."</p>
      <div class="testimonial-author">Aaliyah R.</div>
      <div class="testimonial-role">Nurse Practitioner · Decatur, GA</div>
    </div>
    <div class="testimonial-card">
      <div class="testimonial-stars">★★★★★</div>
      <p class="testimonial-text">"The debt payoff planner showed me I was wasting $4,200/year on interest from the wrong payoff order. Switched to avalanche. Debt-free 2 years early."</p>
      <div class="testimonial-author">Jordan K.</div>
      <div class="testimonial-role">Product Manager · Sandy Springs, GA</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# BUILDER — the convergence of all three songs
# J. Cole's first-gen ambition + Pusha's sovereign hustle + Mavi's quiet dignity
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="section">
  <div class="section-eyebrow">The Builder</div>
  <h2 class="section-h2">Built From the Inside Out</h2>
  <p class="section-sub">No paid counselors. No VC money. No family connections.<br>Just a first-gen student who figured it out — and built the tool he wished he had.</p>

  <div class="builder-card">
    <div class="builder-header">
      {'<img src="' + _HEADSHOT + '" alt="Darrian Belcher" style="width:56px;height:56px;border-radius:50%;object-fit:cover;border:2px solid rgba(201,168,76,0.45);flex-shrink:0;" />' if _HEADSHOT else '<div style="width:56px;height:56px;border-radius:50%;background:rgba(201,168,76,0.15);border:2px solid rgba(201,168,76,0.3);display:flex;align-items:center;justify-content:center;font-size:1.4rem;">🍑</div>'}
      <div>
        <div class="builder-name">Darrian Belcher</div>
        <div class="builder-role">Associate Technical Project Analyst @ Visa · Atlanta, GA · Founder, Peach State Savings</div>
      </div>
    </div>

    <div class="builder-verse">
      "Nobody in my family had navigated a four-year university before me.<br>
      Nobody taught me about RSUs, tax lots, or the difference between<br>
      gross and net — I had to be the one to figure it out.<br><br>
      So I built the tool. Not for clout. Not for a pitch deck.<br>
      For the version of me that needed it three years ago —<br>
      and for everyone else who's been figuring it out alone."
    </div>

    <div class="builder-body">
      Every feature came from a real problem. The bank import? I spent two hours manually
      copying transactions into a spreadsheet. The RSU tracker? I didn't understand my
      Visa equity comp. The sneaker P&amp;L? I was losing track of what I actually made reselling.<br><br>

      This runs 24/7 on a self-hosted homelab in my apartment — Proxmox, Nginx, Docker,
      PostgreSQL. New features are shipped by an <strong style="color:{GOLD};">autonomous AI dev pipeline</strong>
      that runs every night: 6 agents that plan, build, test, and open a GitHub PR while I sleep.
      I wake up, review it, and merge.<br><br>

      <strong style="color:{TEXT_MAIN};">The pipeline does the building. The human makes the decisions.</strong><br>
      That's sovereignty. That's what this app is about.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="section" id="pricing">
  <div class="section-eyebrow">Pricing</div>
  <h2 class="section-h2">Simple. Honest. No Surprises.</h2>
  <p class="section-sub">Start free. Upgrade when you're ready. Cancel anytime — no questions, no dark patterns.</p>
  <div class="pricing-grid">
    <div class="price-card">
      <div class="price-name">Free Plan</div>
      <div><span class="price-dollar">$</span><span class="price-num">0</span></div>
      <div class="price-period">forever · no credit card</div>
      <hr class="price-divider">
      <div class="price-feature"><span class="price-check">✓</span> Monthly budget dashboard</div>
      <div class="price-feature"><span class="price-check">✓</span> Expense tracking &amp; categories</div>
      <div class="price-feature"><span class="price-check">✓</span> Bank statement CSV import</div>
      <div class="price-feature"><span class="price-check">✓</span> Bill calendar</div>
      <div class="price-feature"><span class="price-check">✓</span> Financial goals tracker</div>
      <div class="price-feature"><span class="price-check">✓</span> Income logging</div>
    </div>
    <div class="price-card featured">
      <div class="price-badge">Most Popular</div>
      <div class="price-name">Pro Plan ⭐</div>
      <div><span class="price-dollar">$</span><span class="price-num">4.99</span></div>
      <div class="price-period">per month · cancel anytime</div>
      <hr class="price-divider">
      <div class="price-feature"><span class="price-check">✓</span> Everything in Free</div>
      <div class="price-feature"><span class="price-check">✓</span> AI spending insights (Claude)</div>
      <div class="price-feature"><span class="price-check">✓</span> Net worth tracker</div>
      <div class="price-feature"><span class="price-check">✓</span> RSU &amp; ESPP tracker</div>
      <div class="price-feature"><span class="price-check">✓</span> Investment portfolio tracker</div>
      <div class="price-feature"><span class="price-check">✓</span> Monthly trends &amp; analytics</div>
      <div class="price-feature"><span class="price-check">✓</span> Business income tracker</div>
      <div class="price-feature"><span class="price-check">✓</span> All 73+ Pro tools unlocked</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FOR BUSINESS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="section" id="for-business">
  <div class="section-eyebrow">For Business &amp; Developers</div>
  <h2 class="section-h2">Use It As Your Own</h2>
  <p class="section-sub">License the full platform, run it under your own brand, or own the source code outright.</p>

  <div class="biz-section">
    <div class="biz-grid">
      <div class="biz-card">
        <span class="biz-badge">SaaS Access</span>
        <span class="biz-icon">☁️</span>
        <div class="biz-name">Hosted Agent Access</div>
        <div class="biz-price">$19<span style="font-size:1rem;font-weight:600;">/mo</span></div>
        <div class="biz-price-sub">per seat · cancel anytime</div>
        <p class="biz-desc">Full Peach State Savings AI system — all 73+ tools, dedicated account, priority support, and early feature access. No self-hosting required.</p>
        <hr class="biz-divider">
        <div class="biz-feature"><span class="biz-check">✓</span> All 73+ Pro tools unlocked</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Claude AI spending insights</div>
        <div class="biz-feature"><span class="biz-check">✓</span> RSU, ESPP &amp; portfolio trackers</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Priority support (24hr response)</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Early access to new features</div>
        <div class="biz-cta-note">Contact via LinkedIn to get set up</div>
      </div>

      <div class="biz-card highlight">
        <span class="biz-badge">Most Requested</span>
        <span class="biz-icon">🏢</span>
        <div class="biz-name">Agency White-Label License</div>
        <div class="biz-price">$79<span style="font-size:1rem;font-weight:600;">/mo</span></div>
        <div class="biz-price-sub">per deployment · 20% off annual</div>
        <p class="biz-desc">Deploy the full platform under your own brand for clients, team, or community. Your domain, your logo, your AI finance system — maintained by the same autonomous pipeline.</p>
        <hr class="biz-divider">
        <div class="biz-feature"><span class="biz-check">✓</span> Full white-label branding</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Multi-user management dashboard</div>
        <div class="biz-feature"><span class="biz-check">✓</span> All 73+ tools for your users</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Claude AI under your API key</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Onboarding call included</div>
        <div class="biz-feature"><span class="biz-check">✓</span> You set prices for your users</div>
        <div class="biz-cta-note">Contact via LinkedIn to discuss your deployment</div>
      </div>

      <div class="biz-card">
        <span class="biz-badge">One-Time Purchase</span>
        <span class="biz-icon">📦</span>
        <div class="biz-name">Download &amp; Self-Host</div>
        <div class="biz-price">$249<span style="font-size:1rem;font-weight:600;"> once</span></div>
        <div class="biz-price-sub">lifetime license · no ongoing fees</div>
        <p class="biz-desc">Full source code, Docker Compose, PostgreSQL schema, Nginx config, homelab deployment guide. Run it permanently on your own server. Your data, your hardware, forever.</p>
        <hr class="biz-divider">
        <div class="biz-feature"><span class="biz-check">✓</span> Full Python / Streamlit source code</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Docker Compose + Dockerfile</div>
        <div class="biz-feature"><span class="biz-check">✓</span> PostgreSQL schema + migrations</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Nginx reverse-proxy config</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Lifetime updates via private repo</div>
        <div class="biz-feature"><span class="biz-check">✓</span> One-time 60-min setup call</div>
        <div class="biz-cta-note">Contact via LinkedIn to purchase</div>
      </div>
    </div>

    <p style="text-align:center; margin-top:32px; font-size:0.84rem; color:#7A8499; line-height:1.7;">
      💬 All business inquiries:
      <a href="https://www.linkedin.com/in/darrian-belcher/" target="_blank" rel="noopener noreferrer"
         style="color:#C9A84C; text-decoration:none;">LinkedIn → Darrian Belcher</a>
      · Response within 24 hours.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FAQ
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="section" id="faq">
  <div class="section-eyebrow">FAQ</div>
  <h2 class="section-h2">Straight Answers</h2>
  <p class="section-sub">Everything you need to know before you sign up.</p>

  <div class="faq-item">
    <h3 class="faq-q">Is it really free — no hidden charges?</h3>
    <div class="faq-a">Yes, completely free — no credit card required, no trial period, no surprise charges. The free plan includes budgeting, expense tracking, bank import, bill calendar, and financial goals. It stays free forever.</div>
  </div>
  <div class="faq-item">
    <h3 class="faq-q">Is my data private and secure?</h3>
    <div class="faq-a">Absolutely. Peach State Savings is self-hosted on a private server in Atlanta, GA. Your data is stored in a private PostgreSQL database, never sold, never shared with third parties, never used for advertising.</div>
  </div>
  <div class="faq-item">
    <h3 class="faq-q">Which banks does the import support?</h3>
    <div class="faq-a">The bank statement import supports CSV exports from Navy Federal Credit Union (NFCU), Chase, Bank of America, Wells Fargo, Ally, and most major US banks. Export CSV from your bank's website, paste it in — no credentials required.</div>
  </div>
  <div class="faq-item">
    <h3 class="faq-q">Do I need to connect my actual bank account?</h3>
    <div class="faq-a">No. Peach State Savings does NOT use Plaid, Open Banking, or live bank connections. You import data via CSV export — your banking credentials are never entered into this app.</div>
  </div>
  <div class="faq-item">
    <h3 class="faq-q">Does it support Visa RSU and ESPP tracking?</h3>
    <div class="faq-a">Yes. The RSU/ESPP tracker is built specifically for tech employees with equity compensation. It tracks vest schedules, ESPP purchase periods, tax lots, share price at vest, and estimated net gain after income taxes and broker fees.</div>
  </div>
  <div class="faq-item">
    <h3 class="faq-q">What AI model powers the insights?</h3>
    <div class="faq-a">Peach State Savings uses Anthropic's Claude (claude-opus-4-5) for all AI-powered features including spending categorization, personalized insights, goal predictions, and debt payoff recommendations.</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FINAL CTA — all three songs converge here
# The Pusha flex (earned, stacked), the Cole ambition (I figured it out),
# the Mavi quiet (build in silence, wake up sovereign)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="cta-section">
  <h2 class="cta-h2">
    Wake Up <span class="gold-word">Sovereign</span>.<br>
    Build Like You Already Won.
  </h2>
  <div class="cta-verse">
    You figured out the hard part alone.<br>
    The tool should be the easy part.<br>
    Free. Private. Built in Atlanta.<br>
    For the ones who never had an advisor —<br>
    and never needed one.
  </div>
</div>
""", unsafe_allow_html=True)

cta_l, cta_c, cta_r = st.columns([1, 2, 1])
with cta_c:
    st.markdown("<div style='margin-top:-24px;'></div>", unsafe_allow_html=True)
    if st.button("🍑  Create My Free Account", type="primary", use_container_width=True, key="cta_bottom"):
        st.switch_page("app.py")
    st.markdown(f"""
    <div style='text-align:center; color:{TEXT_MUTED}; font-size:0.76rem; margin-top:10px; line-height:1.7;
                font-family: "EB Garamond", Georgia, serif; font-style: italic;'>
      Secure account with email + password.<br>
      Your data stays private on this server. Free plan is free forever.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    if st.button("Already have an account? Sign In →", use_container_width=True, key="signin_bottom"):
        st.switch_page("app.py")


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="site-footer" role="contentinfo">
  <div class="footer-grid">
    <div>
      <div class="footer-brand">🍑 Peach State Savings</div>
      <p class="footer-tagline">
        Free AI-powered personal finance. Self-hosted in Atlanta, GA.<br>
        Your data stays private — no ads, no selling, no middlemen.
      </p>
    </div>
    <div>
      <div class="footer-col-title">Product</div>
      <span class="footer-link">Features</span>
      <span class="footer-link">Pricing</span>
      <span class="footer-link">FAQ</span>
    </div>
    <div>
      <div class="footer-col-title">Connect</div>
      <a class="footer-link" href="https://www.linkedin.com/in/darrian-belcher/" rel="noopener noreferrer" target="_blank">LinkedIn</a>
      <a class="footer-link" href="https://github.com/bookofdarrian/darrian-budget" rel="noopener noreferrer" target="_blank">GitHub</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>
      © 2026 Peach State Savings ·
      Built &amp; self-hosted in Atlanta, GA by
      <a href="https://www.linkedin.com/in/darrian-belcher/" rel="noopener noreferrer" target="_blank">Darrian Belcher</a>
    </span>
    <span>Free personal finance · AI budgeting · Bank import · RSU tracker</span>
  </div>
  <div class="footer-end-verse">
    "Stack the knowledge. Stack the data. Let the numbers speak for themselves."
  </div>
</div>
""", unsafe_allow_html=True)
