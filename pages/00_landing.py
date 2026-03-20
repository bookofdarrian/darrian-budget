"""
Peach State Savings — Public Landing Page (SEO-Optimized)
No login required. Shown to all visitors before they authenticate.
Designed for peachstatesavings.com — Mobile-first, Core Web Vitals compliant.
"""

import streamlit as st

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
