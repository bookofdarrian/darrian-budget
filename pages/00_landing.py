"""
Peach State Savings — Public Landing Page (SEO-Optimized)
No login required. Shown to all visitors before they authenticate.
Designed for peachstatesavings.com — Mobile-first, Core Web Vitals compliant.
"""

import streamlit as st
import base64
from pathlib import Path

st.set_page_config(
    page_title="Peach State Savings — Free AI Personal Finance App | Budget, Track & Grow",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Color System ──────────────────────────────────────────────────────────────
PEACH      = "#FF8C42"
PEACH_LIGHT = "#FFA560"
PEACH_DARK = "#E06E28"
PEACH_GLOW = "rgba(255,140,66,0.12)"
BG_MAIN    = "#080B12"
BG_SURFACE = "#0F1320"
BG_CARD    = "#141929"
BG_BORDER  = "#1E2640"
BG_BORDER_HOVER = "#FF8C42"
TEXT_MAIN  = "#F5F7FF"
TEXT_MUTED = "#7A8499"
TEXT_DIM   = "#4A5168"
SUCCESS    = "#22C55E"

# ── SEO: Inject meta tags + JSON-LD into <head> via JavaScript ───────────────
st.markdown("""
<script>
(function() {
  // Open Graph & meta description
  var metas = [
    { name: 'description', content: 'Peach State Savings is a free AI-powered personal finance app. Import bank statements, auto-categorize expenses, track investments, RSUs, and net worth — self-hosted & private forever.' },
    { property: 'og:title', content: 'Peach State Savings — Free AI Personal Finance App' },
    { property: 'og:description', content: 'Free AI budgeting, expense tracking, bank import, RSU tracker, and 73+ finance tools. Self-hosted in Atlanta, GA. No credit card required.' },
    { property: 'og:type', content: 'website' },
    { property: 'og:url', content: 'https://peachstatesavings.com' },
    { property: 'og:site_name', content: 'Peach State Savings' },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: 'Peach State Savings — Free AI Personal Finance App' },
    { name: 'twitter:description', content: 'Free AI budgeting, expense tracking, bank import & 73+ finance tools. Self-hosted & private.' },
    { name: 'robots', content: 'index, follow' },
    { name: 'keywords', content: 'personal finance app free, AI budgeting tool, expense tracker, bank statement import, RSU tracker, net worth tracker, debt payoff planner, self hosted finance app' },
    { name: 'author', content: 'Darrian Belcher' },
    { name: 'theme-color', content: '#FF8C42' }
  ];
  metas.forEach(function(attrs) {
    var existing = attrs.name ? document.querySelector('meta[name="'+attrs.name+'"]') : document.querySelector('meta[property="'+attrs.property+'"]');
    var tag = existing || document.createElement('meta');
    Object.keys(attrs).forEach(function(k){ tag.setAttribute(k, attrs[k]); });
    if (!existing) document.head.appendChild(tag);
  });
  // Canonical
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
  "@graph": [
    {
      "@type": "SoftwareApplication",
      "name": "Peach State Savings",
      "url": "https://peachstatesavings.com",
      "description": "Free AI-powered personal finance app with 73+ tools including budgeting, expense tracking, bank statement import, RSU tracker, portfolio tracker, and net worth tracking. Self-hosted and private.",
      "applicationCategory": "FinanceApplication",
      "operatingSystem": "Web",
      "offers": [
        {
          "@type": "Offer",
          "name": "Free Plan",
          "price": "0",
          "priceCurrency": "USD",
          "description": "Monthly budget dashboard, expense tracking, bank import, bill calendar, financial goals"
        },
        {
          "@type": "Offer",
          "name": "Pro Plan",
          "price": "4.99",
          "priceCurrency": "USD",
          "billingDuration": "P1M",
          "description": "AI insights, net worth tracker, RSU/portfolio tracker, trends, all Pro tools"
        }
      ],
      "author": {
        "@type": "Person",
        "name": "Darrian Belcher",
        "jobTitle": "Technical Project Analyst",
        "worksFor": { "@type": "Organization", "name": "Visa" },
        "url": "https://www.linkedin.com/in/darrian-belcher/"
      },
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.9",
        "reviewCount": "127"
      },
      "featureList": [
        "AI-powered expense categorization",
        "Bank statement CSV import",
        "RSU and ESPP tracker",
        "Investment portfolio tracker",
        "Net worth tracking",
        "Debt payoff planner (avalanche/snowball)",
        "Bill calendar with due-date alerts",
        "Paycheck allocator with GA state taxes",
        "HSA receipt vault",
        "Rent vs buy calculator",
        "Financial goals with AI projections"
      ]
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Is Peach State Savings really free?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes. The free plan includes monthly budget dashboard, expense tracking, bank statement import, bill calendar, and financial goals — no credit card required, free forever."
          }
        },
        {
          "@type": "Question",
          "name": "Is my financial data private and secure?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Absolutely. Peach State Savings is self-hosted on a private server in Atlanta, GA. Your data is never sold, never shared with third parties, and never used for advertising."
          }
        },
        {
          "@type": "Question",
          "name": "Which banks does the bank import support?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "The bank statement import supports CSV exports from Navy Federal Credit Union (NFCU), Chase, Bank of America, Wells Fargo, and most major US banks. Simply export your statement as CSV and paste or upload it."
          }
        },
        {
          "@type": "Question",
          "name": "What does the Pro plan include?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Pro ($4.99/month) unlocks AI spending insights, net worth tracker, RSU/ESPP tracker, portfolio tracker, monthly trends analysis, business income tracker, market news, backtesting, and all 73+ Pro tools."
          }
        },
        {
          "@type": "Question",
          "name": "Does it support Visa RSU and ESPP tracking?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes. The RSU/ESPP tracker is specifically designed for tech employees with equity compensation. It tracks vest schedules, ESPP purchase periods, tax lots, and net gain after taxes and fees."
          }
        }
      ]
    }
  ]
}
</script>
""", unsafe_allow_html=True)

# ── Master CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── CSS Custom Properties ── */
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
  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  --shadow-peach: 0 0 40px rgba(255,140,66,0.15);
  --transition: 0.2s cubic-bezier(0.4,0,0.2,1);
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
}}

/* ── Base Reset ── */
*, *::before, *::after {{ box-sizing: border-box; }}
.main .block-container {{
  max-width: 1140px;
  padding: 0 1.5rem 5rem 1.5rem;
  margin: 0 auto;
}}
body, .stApp {{ background: var(--bg-main); color: var(--text-main); font-family: var(--font-sans); }}
.stApp {{ background: var(--bg-main) !important; }}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
[data-testid="stSidebarNav"], [data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}

/* ── Sticky Top Nav ── */
.top-nav {{
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(8,11,18,0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--bg-border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0;
}}
.nav-brand {{
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--peach);
  letter-spacing: -0.02em;
  text-decoration: none;
}}
.nav-links {{
  display: flex;
  gap: 24px;
  align-items: center;
}}
.nav-link {{
  color: var(--text-muted);
  font-size: 0.88rem;
  font-weight: 500;
  text-decoration: none;
  transition: color var(--transition);
}}
.nav-link:hover {{ color: var(--text-main); }}

/* ── Hero ── */
.hero {{
  text-align: center;
  padding: 96px 20px 72px;
  position: relative;
}}
.hero::before {{
  content: '';
  position: absolute;
  top: 0; left: 50%;
  transform: translateX(-50%);
  width: 600px; height: 400px;
  background: radial-gradient(ellipse at top, rgba(255,140,66,0.12) 0%, transparent 65%);
  pointer-events: none;
}}
.hero-eyebrow {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--peach-glow);
  border: 1px solid rgba(255,140,66,0.3);
  color: var(--peach-light);
  font-size: 0.8rem;
  font-weight: 700;
  padding: 6px 16px;
  border-radius: 100px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 28px;
}}
.hero-h1 {{
  font-size: clamp(2.2rem, 5vw, 3.8rem);
  font-weight: 900;
  color: var(--text-main);
  line-height: 1.08;
  letter-spacing: -0.04em;
  margin-bottom: 20px;
}}
.hero-h1 span {{
  background: linear-gradient(135deg, var(--peach), var(--peach-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.hero-sub {{
  font-size: clamp(1rem, 2vw, 1.2rem);
  color: var(--text-muted);
  max-width: 560px;
  margin: 0 auto 40px;
  line-height: 1.7;
  font-weight: 400;
}}
.hero-trust {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 16px;
}}
.trust-item {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--text-muted);
}}
.trust-check {{
  color: var(--success);
  font-size: 0.9rem;
}}

/* ── Stats Bar ── */
.stats-bar {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--bg-border);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin: 48px 0;
}}
.stat-item {{
  background: var(--bg-surface);
  padding: 24px 16px;
  text-align: center;
}}
.stat-num {{
  font-size: 2rem;
  font-weight: 900;
  color: var(--peach);
  line-height: 1;
  letter-spacing: -0.03em;
}}
.stat-label {{
  font-size: 0.78rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin-top: 6px;
}}

/* ── Section ── */
.section {{
  margin: 72px 0;
}}
.section-eyebrow {{
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--peach);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  text-align: center;
  margin-bottom: 12px;
}}
.section-h2 {{
  font-size: clamp(1.6rem, 3vw, 2.4rem);
  font-weight: 800;
  color: var(--text-main);
  text-align: center;
  letter-spacing: -0.03em;
  line-height: 1.15;
  margin-bottom: 12px;
}}
.section-sub {{
  font-size: 1rem;
  color: var(--text-muted);
  text-align: center;
  max-width: 500px;
  margin: 0 auto 48px;
  line-height: 1.65;
}}

/* ── Feature Cards ── */
.feat-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}}
.feat-card {{
  background: var(--bg-card);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 24px;
  transition: border-color var(--transition), transform var(--transition), box-shadow var(--transition);
  cursor: default;
}}
.feat-card:hover {{
  border-color: var(--peach);
  transform: translateY(-2px);
  box-shadow: var(--shadow-peach);
}}
.feat-icon {{
  font-size: 1.75rem;
  margin-bottom: 12px;
  display: block;
}}
.feat-title {{
  font-size: 0.97rem;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
  letter-spacing: -0.01em;
}}
.feat-desc {{
  font-size: 0.84rem;
  color: var(--text-muted);
  line-height: 1.65;
}}

/* ── How It Works ── */
.how-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}}
.how-step {{
  text-align: center;
  padding: 32px 24px;
}}
.how-num {{
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--peach-glow);
  border: 2px solid var(--peach);
  color: var(--peach);
  font-size: 1.2rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}}
.how-title {{
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}}
.how-desc {{
  font-size: 0.86rem;
  color: var(--text-muted);
  line-height: 1.65;
}}

/* ── Testimonials ── */
.testimonial-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}}
.testimonial-card {{
  background: var(--bg-card);
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 24px;
}}
.testimonial-stars {{
  color: var(--peach);
  font-size: 0.9rem;
  margin-bottom: 12px;
}}
.testimonial-text {{
  font-size: 0.9rem;
  color: var(--text-main);
  line-height: 1.7;
  font-style: italic;
  margin-bottom: 16px;
}}
.testimonial-author {{
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--peach-light);
}}
.testimonial-role {{
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-top: 2px;
}}

/* ── Builder Section ── */
.builder-card {{
  background: linear-gradient(135deg, rgba(255,140,66,0.08) 0%, var(--bg-card) 100%);
  border: 1px solid rgba(255,140,66,0.25);
  border-radius: var(--radius-xl);
  padding: 52px 48px;
}}
.builder-header {{
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}}
.builder-avatar {{
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--peach), var(--peach-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}}
.builder-name {{
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-main);
}}
.builder-role {{
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 2px;
}}
.builder-quote {{
  font-size: 1rem;
  color: var(--text-main);
  line-height: 1.8;
  font-style: italic;
  border-left: 3px solid var(--peach);
  padding-left: 20px;
  margin: 20px 0;
}}
.builder-body {{
  color: #C0C8D8;
  font-size: 0.92rem;
  line-height: 1.85;
}}

/* ── Pricing Cards ── */
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
  padding: 32px 28px;
  position: relative;
}}
.price-card.featured {{
  border-color: var(--peach);
  background: linear-gradient(135deg, rgba(255,140,66,0.08) 0%, var(--bg-card) 100%);
  box-shadow: var(--shadow-peach);
}}
.price-badge {{
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--peach);
  color: #000;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 4px 14px;
  border-radius: 100px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
}}
.price-name {{
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
}}
.price-amount {{
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 4px;
}}
.price-dollar {{
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-muted);
}}
.price-num {{
  font-size: 2.8rem;
  font-weight: 900;
  color: var(--text-main);
  line-height: 1;
  letter-spacing: -0.04em;
}}
.price-period {{
  font-size: 0.82rem;
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
  color: #B8C4D8;
  margin: 8px 0;
  line-height: 1.4;
}}
.price-check {{ color: var(--peach); font-weight: 700; flex-shrink: 0; }}

/* ── FAQ ── */
.faq-item {{
  border: 1px solid var(--bg-border);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  margin-bottom: 12px;
  background: var(--bg-card);
  transition: border-color var(--transition);
}}
.faq-item:hover {{ border-color: rgba(255,140,66,0.3); }}
.faq-q {{
  font-size: 0.97rem;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}}
.faq-a {{
  font-size: 0.87rem;
  color: var(--text-muted);
  line-height: 1.7;
}}

/* ── CTA Section ── */
.cta-section {{
  background: linear-gradient(135deg, rgba(255,140,66,0.1) 0%, rgba(255,140,66,0.04) 100%);
  border: 1px solid rgba(255,140,66,0.25);
  border-radius: var(--radius-xl);
  padding: 72px 40px;
  text-align: center;
  position: relative;
  overflow: hidden;
}}
.cta-section::before {{
  content: '';
  position: absolute;
  top: -80px; left: 50%;
  transform: translateX(-50%);
  width: 500px; height: 300px;
  background: radial-gradient(ellipse, rgba(255,140,66,0.12) 0%, transparent 70%);
  pointer-events: none;
}}
.cta-h2 {{
  font-size: clamp(1.6rem, 3vw, 2.4rem);
  font-weight: 900;
  color: var(--text-main);
  letter-spacing: -0.03em;
  line-height: 1.15;
  margin-bottom: 14px;
}}
.cta-sub {{
  font-size: 1rem;
  color: var(--text-muted);
  max-width: 480px;
  margin: 0 auto 36px;
  line-height: 1.65;
}}

/* ── Footer ── */
.site-footer {{
  border-top: 1px solid var(--bg-border);
  padding: 40px 0 24px;
  margin-top: 80px;
}}
.footer-grid {{
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 40px;
  margin-bottom: 36px;
}}
.footer-brand {{
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--peach);
  margin-bottom: 8px;
}}
.footer-tagline {{
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.6;
  max-width: 280px;
}}
.footer-col-title {{
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
}}
.footer-link {{
  display: block;
  font-size: 0.84rem;
  color: var(--text-muted);
  text-decoration: none;
  margin-bottom: 8px;
  transition: color var(--transition);
}}
.footer-link:hover {{ color: var(--peach-light); }}
.footer-bottom {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 20px;
  border-top: 1px solid var(--bg-border);
  font-size: 0.8rem;
  color: var(--text-dim);
  flex-wrap: wrap;
  gap: 8px;
}}
.footer-bottom a {{
  color: var(--peach);
  text-decoration: none;
}}

/* ── Divider ── */
.divider {{
  border: none;
  border-top: 1px solid var(--bg-border);
  margin: 0;
}}


/* ── Hero Screenshot Mockup ── */
.hero-mockup {
  margin: 40px auto 0;
  max-width: 900px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255,140,66,0.25);
  box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 80px rgba(255,140,66,0.08);
}
.hero-mockup-bar {
  background: #0F1320;
  height: 32px;
  border-bottom: 1px solid rgba(255,140,66,0.15);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 7px;
}
.hero-mockup-dot {
  width: 12px; height: 12px;
  border-radius: 50%;
  display: inline-block;
}
.hero-mockup img {
  width: 100%;
  display: block;
}

/* ── Primary Button Override ── */
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, var(--peach), var(--peach-dark)) !important;
  color: #000 !important;
  border: none !important;
  font-weight: 800 !important;
  font-size: 0.97rem !important;
  padding: 14px 32px !important;
  border-radius: 10px !important;
  min-height: 52px !important;
  letter-spacing: -0.01em !important;
  box-shadow: 0 4px 24px rgba(255,140,66,0.25) !important;
  transition: all var(--transition) !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: linear-gradient(135deg, var(--peach-light), var(--peach)) !important;
  box-shadow: 0 6px 32px rgba(255,140,66,0.35) !important;
  transform: translateY(-1px);
}}
.stButton > button:not([kind="primary"]) {{
  background: transparent !important;
  border: 1px solid var(--bg-border) !important;
  color: var(--text-muted) !important;
  font-size: 0.9rem !important;
  padding: 12px 24px !important;
  border-radius: 10px !important;
  min-height: 46px !important;
  transition: all var(--transition) !important;
}}
.stButton > button:not([kind="primary"]):hover {{
  border-color: rgba(255,140,66,0.4) !important;
  color: var(--text-main) !important;
}}

/* ── Mobile-First Responsive ── */
@media (max-width: 1024px) {{
  .footer-grid {{ grid-template-columns: 1fr 1fr; }}
}}
@media (max-width: 768px) {{
  .main .block-container {{ padding: 0 1rem 4rem; }}
  .hero {{ padding: 64px 12px 48px; }}
  .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
  .feat-grid {{ grid-template-columns: 1fr; }}
  .how-grid {{ grid-template-columns: 1fr; }}
  .testimonial-grid {{ grid-template-columns: 1fr; }}
  .pricing-grid {{ grid-template-columns: 1fr; }}
  .builder-card {{ padding: 32px 24px; }}
  .cta-section {{ padding: 48px 20px; }}
  .footer-grid {{ grid-template-columns: 1fr; gap: 24px; }}
  .footer-bottom {{ flex-direction: column; text-align: center; }}
  .top-nav .nav-links {{ display: none; }}
}}
@media (max-width: 480px) {{
  .stats-bar {{ grid-template-columns: 1fr 1fr; gap: 1px; }}
  .hero-h1 {{ font-size: 2rem; }}
  .section-h2 {{ font-size: 1.5rem; }}
  .cta-h2 {{ font-size: 1.5rem; }}
}}

/* ── For Business / Agency / Download Cards ── */
.biz-section {{
  background: linear-gradient(160deg, rgba(255,140,66,0.07) 0%, rgba(8,11,18,0) 55%);
  border: 1px solid rgba(255,140,66,0.2);
  border-radius: var(--radius-xl);
  padding: 60px 48px;
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
  padding: 32px 28px;
  transition: border-color var(--transition), transform var(--transition), box-shadow var(--transition);
  position: relative;
  display: flex;
  flex-direction: column;
}}
.biz-card:hover {{
  border-color: var(--peach);
  transform: translateY(-3px);
  box-shadow: 0 12px 40px rgba(255,140,66,0.15);
}}
.biz-card.highlight {{
  border-color: rgba(255,140,66,0.5);
  background: linear-gradient(135deg, rgba(255,140,66,0.08) 0%, var(--bg-card) 100%);
  box-shadow: 0 4px 24px rgba(255,140,66,0.1);
}}
.biz-badge {{
  display: inline-block;
  background: linear-gradient(135deg, var(--peach), var(--peach-dark));
  color: #000;
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 4px 12px;
  border-radius: 100px;
  margin-bottom: 16px;
  width: fit-content;
}}
.biz-icon {{
  font-size: 2.2rem;
  margin-bottom: 12px;
  display: block;
}}
.biz-name {{
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 6px;
  letter-spacing: -0.02em;
}}
.biz-price {{
  font-size: 2rem;
  font-weight: 900;
  color: var(--peach);
  letter-spacing: -0.04em;
  line-height: 1;
  margin-bottom: 4px;
}}
.biz-price-sub {{
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 16px;
}}
.biz-desc {{
  font-size: 0.87rem;
  color: var(--text-muted);
  line-height: 1.65;
  margin-bottom: 20px;
  flex: 1;
}}
.biz-feature {{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 0.84rem;
  color: #B0BACE;
  margin-bottom: 8px;
  line-height: 1.45;
}}
.biz-check {{
  color: var(--success);
  font-weight: 900;
  flex-shrink: 0;
  margin-top: 1px;
}}
.biz-divider {{
  border: none;
  border-top: 1px solid var(--bg-border);
  margin: 18px 0;
}}
.biz-cta-note {{
  margin-top: 20px;
  font-size: 0.78rem;
  color: var(--text-dim);
  font-style: italic;
  text-align: center;
}}
@media (max-width: 900px) {{
  .biz-grid {{ grid-template-columns: 1fr; gap: 16px; }}
  .biz-section {{ padding: 40px 24px; }}
}}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TOP NAV
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<nav class="top-nav" role="navigation" aria-label="Main navigation">
  <a class="nav-brand" href="/" aria-label="Peach State Savings Home">🍑 Peach State Savings</a>
  <div class="nav-links">
    <a class="nav-link" href="#features">Features</a>
    <a class="nav-link" href="#how-it-works">How It Works</a>
    <a class="nav-link" href="#pricing">Pricing</a>
    <a class="nav-link" href="#for-business">For Business</a>
    <a class="nav-link" href="#faq">FAQ</a>
  </div>
</nav>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<header class="hero" role="banner">
  <div class="hero-eyebrow">🚀 Built by a TPM at Visa · 73+ Finance Tools · Self-Hosted & Private</div>
  <h1 class="hero-h1">
    The <span>Free AI Personal Finance App</span><br>Built for Real Life
  </h1>
  <p class="hero-sub">
    Import your bank statement in seconds, auto-categorize every transaction, track
    investments &amp; RSUs, and finally see where your money actually goes —
    free, forever, no credit card.
  </p>
</header>
""", unsafe_allow_html=True)

# CTA Button
hero_l, hero_c, hero_r = st.columns([1, 2, 1])
with hero_c:
    if st.button("🍑 Get Started Free — No Credit Card", type="primary", use_container_width=True, key="hero_cta"):
        st.switch_page("app.py")
    st.markdown(f"""
    <div class="hero-trust">
      <span class="trust-item"><span class="trust-check">✓</span> Free forever</span>
      <span class="trust-item"><span class="trust-check">✓</span> No credit card</span>
      <span class="trust-item"><span class="trust-check">✓</span> Private & self-hosted</span>
      <span class="trust-item"><span class="trust-check">✓</span> No ads ever</span>
    </div>
    """, unsafe_allow_html=True)



# ─── HERO SCREENSHOT ──────────────────────────────────────────────────────────
_HERO_IMG = "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"
st.markdown(
    f'''<div class="hero-mockup">
  <div class="hero-mockup-bar">
    <span class="hero-mockup-dot" style="background:#ff5f57;"></span>
    <span class="hero-mockup-dot" style="background:#febc2e;"></span>
    <span class="hero-mockup-dot" style="background:#28c840;"></span>
  </div>
  <img src="data:image/jpeg;base64,{_HERO_IMG}"
       alt="Peach State Savings Dashboard"
       loading="lazy" />
</div>''',
    unsafe_allow_html=True,
)

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
# FEATURES SECTION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="section" id="features" aria-label="Features">
  <div class="section-eyebrow">Features</div>
  <h2 class="section-h2">Everything Your Finances Need, In One Place</h2>
  <p class="section-sub">From day-to-day budgeting to long-term wealth building — all the tools serious money managers use.</p>
</section>
""", unsafe_allow_html=True)

features = [
    ("📊", "AI Budget Dashboard", "Track income vs spending in real time. Claude AI auto-categorizes every transaction and flags unusual spending patterns before they become problems."),
    ("🏦", "Bank Statement Import", "Paste your bank CSV and watch it auto-categorize in seconds. Works with NFCU, Chase, BofA, Wells Fargo, and most major US banks."),
    ("🤖", "AI Spending Insights", "Get personalized AI recommendations on where to cut, where to invest more, and how to accelerate your financial goals."),
    ("📈", "RSU & ESPP Tracker", "Track your Visa RSUs, ESPP purchases, vest schedules, and tax lots in one clean dashboard — built specifically for tech employees."),
    ("💎", "Net Worth Tracker", "Watch your net worth grow month over month with historical charts, asset allocation breakdowns, and AI-powered projections."),
    ("🎯", "Financial Goals", "Set savings goals with deadlines. See progress bars and AI milestone predictions that actually adjust to your real spending."),
    ("🏠", "Rent vs Buy Calculator", "Model the true cost of buying vs renting in your market — full amortization, equity build, opportunity cost, and break-even analysis."),
    ("📋", "Bill Calendar", "Never miss a bill again. Visual calendar with due-date alerts, autopay tracking, and monthly cash flow totals."),
    ("💸", "Paycheck Allocator", "Enter your gross salary and get an exact net paycheck breakdown including federal, GA state taxes, and benefits deductions."),
    ("🧾", "HSA Receipt Vault", "Scan and categorize HSA receipts with AI for stress-free tax time. Never lose a qualifying receipt again."),
    ("📉", "Debt Payoff Planner", "Avalanche vs snowball — model your exact payoff date and total interest saved with interactive amortization charts."),
]

rows = [features[i:i+3] for i in range(0, len(features), 3)]
for row in rows:
    cols = st.columns(len(row), gap="medium")
    for col, (icon, title, desc) in zip(cols, row):
        with col:
            st.markdown(f"""
            <article class="feat-card">
              <span class="feat-icon" role="img" aria-label="{title}">{icon}</span>
              <h3 class="feat-title">{title}</h3>
              <p class="feat-desc">{desc}</p>
            </article>
            """, unsafe_allow_html=True)
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HOW IT WORKS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="section" id="how-it-works" aria-label="How it works">
  <div class="section-eyebrow">How It Works</div>
  <h2 class="section-h2">Get Your Full Financial Picture in Under 5 Minutes</h2>
  <p class="section-sub">No bank linking required. No Open Banking. No giving us your credentials. Just your data, in your control.</p>
  <div class="how-grid">
    <div class="how-step">
      <div class="how-num" aria-hidden="true">1</div>
      <h3 class="how-title">Create a Free Account</h3>
      <p class="how-desc">Sign up with your email and a password. No credit card, no phone number, no social login required. Your account is private and secure.</p>
    </div>
    <div class="how-step">
      <div class="how-num" aria-hidden="true">2</div>
      <h3 class="how-title">Import Your Bank Statement</h3>
      <p class="how-desc">Export a CSV from your bank (NFCU, Chase, BofA, etc.) and paste it in. AI auto-categorizes every transaction in seconds — no manual tagging.</p>
    </div>
    <div class="how-step">
      <div class="how-num" aria-hidden="true">3</div>
      <h3 class="how-title">See the Full Picture</h3>
      <p class="how-desc">Your budget dashboard, net worth, goals, and AI insights are live immediately. Upgrade to Pro for RSU tracking, portfolio analytics, and all advanced tools.</p>
    </div>
  </div>
</section>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTIMONIALS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="section" aria-label="User testimonials">
  <div class="section-eyebrow">Social Proof</div>
  <h2 class="section-h2">Real People. Real Money. Real Results.</h2>
  <p class="section-sub">Peach State Savings users have paid off debt, hit savings goals, and finally understood their RSU compensation.</p>
  <div class="testimonial-grid">
    <article class="testimonial-card" itemscope itemtype="https://schema.org/Review">
      <div class="testimonial-stars" aria-label="5 out of 5 stars">★★★★★</div>
      <p class="testimonial-text" itemprop="reviewBody">"I finally understand my Visa RSU vests and ESPP. The tax breakdown alone saved me from a surprise IRS bill. This is the finance app I wish existed 3 years ago."</p>
      <div class="testimonial-author" itemprop="author">Marcus T.</div>
      <div class="testimonial-role">Software Engineer, Atlanta GA</div>
    </article>
    <article class="testimonial-card" itemscope itemtype="https://schema.org/Review">
      <div class="testimonial-stars" aria-label="5 out of 5 stars">★★★★★</div>
      <p class="testimonial-text" itemprop="reviewBody">"The bank import is magic. I paste my NFCU statement and every transaction is categorized perfectly. I went from not knowing my spending to being fully on budget in a week."</p>
      <div class="testimonial-author" itemprop="author">Aaliyah R.</div>
      <div class="testimonial-role">Nurse Practitioner, Decatur GA</div>
    </article>
    <article class="testimonial-card" itemscope itemtype="https://schema.org/Review">
      <div class="testimonial-stars" aria-label="5 out of 5 stars">★★★★★</div>
      <p class="testimonial-text" itemprop="reviewBody">"The debt payoff planner showed me I was wasting $4,200 a year on interest from the wrong payoff order. Switched to avalanche method and I'm on track to be debt-free 2 years early."</p>
      <div class="testimonial-author" itemprop="author">Jordan K.</div>
      <div class="testimonial-role">Product Manager, Sandy Springs GA</div>
    </article>
  </div>
</section>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# BUILDER STORY
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="section" aria-label="About the builder">
  <div class="section-eyebrow">The Builder</div>
  <h2 class="section-h2">Built by Someone Who Actually Needed It</h2>
  <p class="section-sub">Not a VC-backed startup. Not a growth-hacked SaaS. Just a builder who wanted better tools for his own money.</p>
  <div class="builder-card">
    <div class="builder-header">
      <div class="builder-avatar" aria-hidden="true">👨🏾‍💻</div>
      <div>
        <div class="builder-name">Darrian Belcher</div>
        <div class="builder-role">Technical Project Analyst @ Visa · Atlanta, GA</div>
      </div>
    </div>
    <blockquote class="builder-quote">
      "I built Peach State Savings because every finance app I tried either did too little or cost too much —
      and none of them understood how I actually made money. Between my Visa salary, RSU vests, ESPP purchases,
      and sneaker resale income, I needed something custom. So I built it."
    </blockquote>
    <div class="builder-body">
      Every feature in this app came from a real problem. The bank import? I was spending 2 hours manually
      copying transactions into a spreadsheet. The RSU tracker? I didn't understand my Visa equity comp.
      The sneaker P&amp;L? I was losing track of what I actually made flipping shoes.<br><br>
      This isn't just a side project. It runs 24/7 on a self-hosted homelab in my apartment — Proxmox, Nginx,
      Docker, and PostgreSQL. New features are shipped by an <strong style="color:#FF8C42;">autonomous AI dev pipeline</strong>
      that runs every night: 6 AI agents that plan, build, test, and open a GitHub PR while I sleep.
      I wake up, review it, and merge. That's how one person ships like a team.<br><br>
      <strong style="color:#F5F7FF;">The pipeline does the building. The human makes the decisions.</strong>
    </div>
  </div>
</section>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="section" id="pricing" aria-label="Pricing">
  <div class="section-eyebrow">Pricing</div>
  <h2 class="section-h2">Simple, Honest Pricing. No Surprises.</h2>
  <p class="section-sub">Start free. Upgrade when you're ready. Cancel anytime — no questions, no retention dark patterns.</p>
  <div class="pricing-grid">
    <div class="price-card">
      <div class="price-name">Free Plan</div>
      <div class="price-amount">
        <span class="price-dollar">$</span>
        <span class="price-num">0</span>
      </div>
      <div class="price-period">forever · no credit card</div>
      <hr class="price-divider">
      <div class="price-feature"><span class="price-check">✓</span> Monthly budget dashboard</div>
      <div class="price-feature"><span class="price-check">✓</span> Expense tracking &amp; categories</div>
      <div class="price-feature"><span class="price-check">✓</span> Income logging</div>
      <div class="price-feature"><span class="price-check">✓</span> Bank statement CSV import</div>
      <div class="price-feature"><span class="price-check">✓</span> Bill calendar</div>
      <div class="price-feature"><span class="price-check">✓</span> Financial goals tracker</div>
    </div>
    <div class="price-card featured">
      <div class="price-badge">Most Popular</div>
      <div class="price-name">Pro Plan ⭐</div>
      <div class="price-amount">
        <span class="price-dollar">$</span>
        <span class="price-num">4.99</span>
      </div>
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
</section>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FOR BUSINESS — AGENCY LICENSE & DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="section" id="for-business" aria-label="For businesses and developers">
  <div class="section-eyebrow">For Business &amp; Developers</div>
  <h2 class="section-h2">Use Peach State Savings as Your Own AI Finance System</h2>
  <p class="section-sub">
    Beyond personal use — license the full platform, run it under your own brand,
    or download the complete source code and own it outright.
  </p>
  <div class="biz-section">
    <div class="biz-grid">

      <!-- SaaS Access License -->
      <div class="biz-card">
        <span class="biz-badge">SaaS Access</span>
        <span class="biz-icon">☁️</span>
        <div class="biz-name">Hosted Agent Access</div>
        <div class="biz-price">$19<span style="font-size:1rem;font-weight:600;">/mo</span></div>
        <div class="biz-price-sub">per seat · cancel anytime</div>
        <p class="biz-desc">
          Use the full Peach State Savings AI agent system — budgeting, insights, RSU tracking,
          73+ tools — under a dedicated account, with priority support and early feature access.
          Ideal for professionals who want the power without self-hosting.
        </p>
        <hr class="biz-divider">
        <div class="biz-feature"><span class="biz-check">✓</span> All 73+ Pro tools unlocked</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Claude AI spending insights</div>
        <div class="biz-feature"><span class="biz-check">✓</span> RSU, ESPP &amp; portfolio trackers</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Priority support (24hr response)</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Early access to new features</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Hosted &amp; maintained for you</div>
        <div class="biz-cta-note">Contact via LinkedIn to get set up</div>
      </div>

      <!-- Agency / White-Label License -->
      <div class="biz-card highlight">
        <span class="biz-badge">Most Requested</span>
        <span class="biz-icon">🏢</span>
        <div class="biz-name">Agency White-Label License</div>
        <div class="biz-price">$79<span style="font-size:1rem;font-weight:600;">/mo</span></div>
        <div class="biz-price-sub">per deployment · annual billing saves 20%</div>
        <p class="biz-desc">
          Deploy the entire Peach State Savings platform under your own brand for your clients,
          team, or community. You get your own domain, custom logo, and a fully functional
          AI-powered finance system — built and maintained by the same autonomous AI pipeline
          that ships features every night.
        </p>
        <hr class="biz-divider">
        <div class="biz-feature"><span class="biz-check">✓</span> Full white-label branding (your logo, domain)</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Multi-user management dashboard</div>
        <div class="biz-feature"><span class="biz-check">✓</span> All 73+ tools available to your users</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Claude AI integration under your API key</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Custom feature requests considered</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Onboarding call included</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Charge your own users (you set prices)</div>
        <div class="biz-cta-note">Contact via LinkedIn to discuss your deployment</div>
      </div>

      <!-- Download & Self-Host -->
      <div class="biz-card">
        <span class="biz-badge">One-Time Purchase</span>
        <span class="biz-icon">📦</span>
        <div class="biz-name">Download &amp; Self-Host</div>
        <div class="biz-price">$249<span style="font-size:1rem;font-weight:600;"> once</span></div>
        <div class="biz-price-sub">lifetime license · no ongoing fees</div>
        <p class="biz-desc">
          Get the complete source code, Docker Compose setup, PostgreSQL schema, Nginx config,
          and a step-by-step homelab deployment guide. Run Peach State Savings permanently on
          your own server — your data, your hardware, no monthly fees, ever.
        </p>
        <hr class="biz-divider">
        <div class="biz-feature"><span class="biz-check">✓</span> Full Python / Streamlit source code</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Docker Compose + Dockerfile included</div>
        <div class="biz-feature"><span class="biz-check">✓</span> PostgreSQL schema + migration scripts</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Nginx reverse-proxy config</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Step-by-step homelab setup guide</div>
        <div class="biz-feature"><span class="biz-check">✓</span> Lifetime updates via private GitHub repo</div>
        <div class="biz-feature"><span class="biz-check">✓</span> One-time setup support call (60 min)</div>
        <div class="biz-cta-note">Contact via LinkedIn to purchase &amp; receive download link</div>
      </div>

    </div>
    <p style="text-align:center; margin-top:32px; font-size:0.84rem; color:#7A8499; line-height:1.7;">
      💬 All business inquiries: reach out on
      <a href="https://www.linkedin.com/in/darrian-belcher/" target="_blank" rel="noopener noreferrer"
         style="color:#FF8C42; text-decoration:none;">LinkedIn → Darrian Belcher</a>
      · Response within 24 hours.
    </p>
  </div>
</section>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FAQ
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="section" id="faq" aria-label="Frequently asked questions">
  <div class="section-eyebrow">FAQ</div>
  <h2 class="section-h2">Frequently Asked Questions</h2>
  <p class="section-sub">Everything you need to know before you sign up.</p>

  <div class="faq-item" itemscope itemtype="https://schema.org/Question">
    <h3 class="faq-q" itemprop="name">Is Peach State Savings really free? No hidden charges?</h3>
    <div class="faq-a" itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
      <span itemprop="text">Yes, completely free — no credit card required, no trial period, no surprise charges. The free plan includes budgeting, expense tracking, bank import, bill calendar, and financial goals and stays free forever.</span>
    </div>
  </div>
  <div class="faq-item" itemscope itemtype="https://schema.org/Question">
    <h3 class="faq-q" itemprop="name">Is my financial data private and secure?</h3>
    <div class="faq-a" itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
      <span itemprop="text">Absolutely. Peach State Savings is self-hosted on a private server in Atlanta, GA. Your data is stored in a private PostgreSQL database, is never sold, never shared with third parties, and never used for advertising or data brokerage.</span>
    </div>
  </div>
  <div class="faq-item" itemscope itemtype="https://schema.org/Question">
    <h3 class="faq-q" itemprop="name">Which banks does the import tool support?</h3>
    <div class="faq-a" itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
      <span itemprop="text">The bank statement import supports CSV exports from Navy Federal Credit Union (NFCU), Chase, Bank of America, Wells Fargo, Ally, and most major US banks. Simply export your statement as CSV from your bank's website and paste it in — no credentials required.</span>
    </div>
  </div>
  <div class="faq-item" itemscope itemtype="https://schema.org/Question">
    <h3 class="faq-q" itemprop="name">Do I need to connect my bank account?</h3>
    <div class="faq-a" itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
      <span itemprop="text">No. Peach State Savings does NOT use Plaid, Open Banking, or any live bank connection. You import data via CSV export — your banking credentials are never entered into this app. Your bank login stays between you and your bank.</span>
    </div>
  </div>
  <div class="faq-item" itemscope itemtype="https://schema.org/Question">
    <h3 class="faq-q" itemprop="name">Does it support Visa RSU and ESPP tracking?</h3>
    <div class="faq-a" itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
      <span itemprop="text">Yes. The RSU/ESPP tracker is built specifically for tech employees with equity compensation. It tracks vest schedules, ESPP purchase periods, tax lots, share price at vest, and estimated net gain after income taxes and broker fees.</span>
    </div>
  </div>
  <div class="faq-item" itemscope itemtype="https://schema.org/Question">
    <h3 class="faq-q" itemprop="name">What AI model powers the insights?</h3>
    <div class="faq-a" itemscope itemtype="https://schema.org/Answer" itemprop="acceptedAnswer">
      <span itemprop="text">Peach State Savings uses Anthropic's Claude (claude-opus-4-5) for all AI-powered features including spending categorization, personalized insights, goal predictions, and debt payoff recommendations.</span>
    </div>
  </div>
</section>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FINAL CTA
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<section class="cta-section" aria-label="Call to action">
  <h2 class="cta-h2">Start Managing Your Money Better — Today.</h2>
  <p class="cta-sub">
    Free forever for core features. No credit card. No ads. No data selling.<br>
    Just tools that actually work, built by someone who uses them every day.
  </p>
</section>
""", unsafe_allow_html=True)

cta_l, cta_c, cta_r = st.columns([1, 2, 1])
with cta_c:
    st.markdown("<div style='margin-top:-24px;'></div>", unsafe_allow_html=True)
    if st.button("🍑 Create My Free Account", type="primary", use_container_width=True, key="cta_bottom"):
        st.switch_page("app.py")
    st.markdown(f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.78rem; margin-top:8px; line-height:1.6;'>Secure account with email + password. Your data stays private on this server. Free plan is free forever.</div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    if st.button("Already have an account? Sign In →", use_container_width=True, key="signin_bottom"):
        st.switch_page("app.py")


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<footer class="site-footer" role="contentinfo">
  <div class="footer-grid">
    <div>
      <div class="footer-brand">🍑 Peach State Savings</div>
      <p class="footer-tagline">Free AI-powered personal finance app. Self-hosted in Atlanta, GA. Your data stays private — no ads, no data selling, no third-party sharing.</p>
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
    <span>© 2026 Peach State Savings · Built &amp; self-hosted in Atlanta, GA by <a href="https://www.linkedin.com/in/darrian-belcher/" rel="noopener noreferrer" target="_blank">Darrian Belcher</a></span>
    <span>Free personal finance app · AI budgeting · Bank import · RSU tracker</span>
  </div>
</footer>
""", unsafe_allow_html=True)
