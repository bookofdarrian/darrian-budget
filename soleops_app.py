"""
SoleOps — Standalone Streamlit Entry Point (SEO-Optimized)
Port: 8502 | Domain: getsoleops.com (backup: soleops.net)
Run: streamlit run soleops_app.py --server.port=8502 --server.address=0.0.0.0

Public landing page shown to unauthenticated visitors (Googlebot-indexable).
Mobile-first design · Core Web Vitals compliant · JSON-LD structured data.
Authenticated users see the full dashboard with live inventory metrics.
"""

import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from utils.carousel import (
    CAROUSEL_BASE_CSS,
    carousel_theme_css,
    render_shoe_product_carousel,
    render_street_fashion_carousel,
    render_nature_inspiration_carousel,
    render_story_band_html,
    render_roots_cities_band,
    render_headshot_lifestyle_carousel,
)
from utils.db import init_db, get_conn
from utils.auth import (
    inject_soleops_css,
    render_sidebar_brand,
    render_sidebar_user_widget,
    get_current_user,
)

st.set_page_config(
    page_title="SoleOps — Sneaker Reseller Operations Platform | AI Tools for Resellers",
    page_icon="👟",
    layout="wide",
)

init_db()
inject_soleops_css()

user = get_current_user()

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC LANDING PAGE — shown to unauthenticated visitors + Googlebot
# ═══════════════════════════════════════════════════════════════════════════════
if not user:

    # ── Hide sidebar for landing page ─────────────────────────────────────────
    st.html("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """)

    # ── SEO: Meta tags + JSON-LD injected to <head> via JS ───────────────────
    st.html("""
    <script>
    (function() {
      var metas = [
        { name: 'description', content: 'SoleOps is the all-in-one sneaker reseller operations platform. Real-time eBay & Mercari price alerts, AI listing generator, P&L dashboard, arbitrage scanner, and stale inventory AI. Free tier available.' },
        { property: 'og:title', content: 'SoleOps — Sneaker Reseller Operations Platform' },
        { property: 'og:description', content: 'Real-time price alerts, AI listings, P&L tracking, arb scanner. Built by a reseller, for resellers. Free tier, no credit card.' },
        { property: 'og:type', content: 'website' },
        { property: 'og:url', content: 'https://getsoleops.com' },
        { property: 'og:site_name', content: 'SoleOps' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: 'SoleOps — Sneaker Reseller Operations Platform' },
        { name: 'twitter:description', content: 'AI-powered tools for serious sneaker resellers. Price alerts, listings, P&L, arbitrage scanner.' },
        { name: 'robots', content: 'index, follow' },
        { name: 'keywords', content: 'sneaker reseller software, eBay price alert sneakers, Mercari reseller tools, sneaker P&L tracker, arbitrage scanner sneakers, AI listing generator eBay, reseller operations platform, sneaker inventory management' },
        { name: 'author', content: 'Darrian Belcher' },
        { name: 'theme-color', content: '#00D4FF' }
      ];
      metas.forEach(function(attrs) {
        var existing = attrs.name ? document.querySelector('meta[name="'+attrs.name+'"]') : document.querySelector('meta[property="'+attrs.property+'"]');
        var tag = existing || document.createElement('meta');
        Object.keys(attrs).forEach(function(k){ tag.setAttribute(k, attrs[k]); });
        if (!existing) document.head.appendChild(tag);
      });
      if (!document.querySelector('link[rel="canonical"]')) {
        var link = document.createElement('link');
        link.rel = 'canonical'; link.href = 'https://getsoleops.com';
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
          "name": "SoleOps",
          "url": "https://getsoleops.com",
          "description": "SoleOps is the all-in-one operations platform for serious sneaker resellers. Real-time eBay and Mercari price alerts, AI-generated listings, P&L dashboard, arbitrage scanner, stale inventory AI, and inventory management.",
          "applicationCategory": "BusinessApplication",
          "operatingSystem": "Web",
          "offers": [
            {
              "@type": "Offer",
              "name": "Free",
              "price": "0",
              "priceCurrency": "USD",
              "description": "5 inventory items, manual price lookup, basic P&L view"
            },
            {
              "@type": "Offer",
              "name": "Starter",
              "price": "9.99",
              "priceCurrency": "USD",
              "billingDuration": "P1M",
              "description": "50 inventory items, Telegram alerts, AI listing generator, full P&L"
            },
            {
              "@type": "Offer",
              "name": "Pro",
              "price": "19.99",
              "priceCurrency": "USD",
              "billingDuration": "P1M",
              "description": "Unlimited inventory, arbitrage scanner, stale inventory AI, price advisor"
            },
            {
              "@type": "Offer",
              "name": "Pro+",
              "price": "29.99",
              "priceCurrency": "USD",
              "billingDuration": "P1M",
              "description": "Everything in Pro plus direct API listing, multi-user, priority support"
            }
          ],
          "author": {
            "@type": "Person",
            "name": "Darrian Belcher",
            "url": "https://www.linkedin.com/in/darrian-belcher/"
          },
          "featureList": [
            "Real-time eBay and Mercari price monitoring",
            "Telegram price drop alerts",
            "AI-powered eBay and Mercari listing generator",
            "Per-pair P&L after platform fees",
            "Arbitrage scanner with watchlist",
            "Stale inventory detection and AI markdown strategy",
            "Full inventory management with SKU and COGS tracking",
            "Schedule C tax summary",
            "AI resale price advisor"
          ]
        },
        {
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "Is SoleOps free to use?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. SoleOps has a free tier that includes 5 inventory items, manual price lookup, and basic P&L view — no credit card required. Paid plans start at $9.99/month for more inventory slots, Telegram alerts, and AI listings."
              }
            },
            {
              "@type": "Question",
              "name": "How do the real-time price alerts work?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "SoleOps monitors eBay and Mercari for your tracked SKUs. When a comp drops below your target sell price or a target pair appears below your buy threshold, you receive an instant Telegram notification — so you can act before anyone else."
              }
            },
            {
              "@type": "Question",
              "name": "What platforms does the AI listing generator support?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "The AI listing generator (powered by Claude) creates keyword-optimized titles and descriptions for both eBay and Mercari. Better copy means more views, faster sales, and higher final sale prices."
              }
            },
            {
              "@type": "Question",
              "name": "How does the arbitrage scanner work?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "You add pairs to your watchlist with a maximum buy price. SoleOps continuously scans Mercari for those SKUs and fires a Telegram alert the moment a listing appears below your threshold. Never miss a flip again."
              }
            },
            {
              "@type": "Question",
              "name": "Does SoleOps help with taxes?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. The P&L dashboard tracks per-pair net profit after eBay (13.25%) and Mercari (10%) fees, and generates a Schedule C summary for self-employment tax reporting. Your accountant will thank you."
              }
            }
          ]
        }
      ]
    }
    </script>
    """)

    # ── Master CSS ─────────────────────────────────────────────────────────────
    st.html("""
    <style>
    /* ── CSS Custom Properties ── */
    :root {
      --cyan: #00D4FF;
      --cyan-dim: rgba(0,212,255,0.12);
      --cyan-glow: rgba(0,212,255,0.18);
      --purple: #7B2FBE;
      --purple-light: #B06AFF;
      --bg-main: #06080F;
      --bg-surface: #0A0C18;
      --bg-card: #0E1022;
      --bg-border: #181C38;
      --text-main: #F0F4FF;
      --text-muted: #7A80A0;
      --text-dim: #3A3F5A;
      --success: #22D47E;
      --warn: #FFB347;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-xl: 28px;
      --shadow-cyan: 0 0 40px rgba(0,212,255,0.12);
      --grad-text: linear-gradient(135deg, #00D4FF, #B06AFF);
      --transition: 0.2s cubic-bezier(0.4,0,0.2,1);
      --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif;
    }

    /* ── Base ── */
    *, *::before, *::after { box-sizing: border-box; }
    .block-container {
      max-width: 1140px;
      padding: 0 1.5rem 5rem 1.5rem;
      margin: 0 auto;
    }
    body, .stApp { background: var(--bg-main); color: var(--text-main); font-family: var(--font-sans); }
    .stApp { background: var(--bg-main) !important; }

    /* ── Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }

    /* ── Top Nav ── */
    .so-nav {
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(6,8,15,0.88);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border-bottom: 1px solid var(--bg-border);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .so-nav-brand {
      font-size: 1.1rem;
      font-weight: 800;
      background: var(--grad-text);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.02em;
      text-decoration: none;
    }
    .so-nav-links { display: flex; gap: 24px; align-items: center; }
    .so-nav-link {
      color: var(--text-muted);
      font-size: 0.88rem;
      font-weight: 500;
      text-decoration: none;
      transition: color var(--transition);
    }
    .so-nav-link:hover { color: var(--text-main); }

    /* ── Hero ── */
    .so-hero {
      text-align: center;
      padding: 96px 20px 72px;
      position: relative;
    }
    .so-hero::before {
      content: '';
      position: absolute;
      top: 0; left: 50%;
      transform: translateX(-50%);
      width: 700px; height: 450px;
      background: radial-gradient(ellipse at top, rgba(0,212,255,0.08) 0%, rgba(123,47,190,0.05) 40%, transparent 70%);
      pointer-events: none;
    }
    .so-eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--cyan-dim);
      border: 1px solid rgba(0,212,255,0.3);
      color: var(--cyan);
      font-size: 0.78rem;
      font-weight: 700;
      padding: 5px 14px;
      border-radius: 100px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin-bottom: 28px;
    }
    .so-h1 {
      font-size: clamp(2.2rem, 5vw, 3.8rem);
      font-weight: 900;
      color: var(--text-main);
      line-height: 1.08;
      letter-spacing: -0.04em;
      margin-bottom: 20px;
    }
    .so-h1 span {
      background: var(--grad-text);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .so-hero-sub {
      font-size: clamp(1rem, 2vw, 1.2rem);
      color: var(--text-muted);
      max-width: 580px;
      margin: 0 auto 40px;
      line-height: 1.7;
    }
    .so-trust {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 20px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    .so-trust-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.82rem;
      color: var(--text-muted);
    }
    .so-trust-check { color: var(--success); }

    /* ── Stats Bar ── */
    .so-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1px;
      background: var(--bg-border);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-lg);
      overflow: hidden;
      margin: 48px 0;
    }
    .so-stat {
      background: var(--bg-surface);
      padding: 24px 16px;
      text-align: center;
    }
    .so-stat-num {
      font-size: 1.9rem;
      font-weight: 900;
      background: var(--grad-text);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      line-height: 1;
      letter-spacing: -0.03em;
    }
    .so-stat-label {
      font-size: 0.77rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.07em;
      margin-top: 6px;
    }

    /* ── Sections ── */
    .so-section { margin: 72px 0; }
    .so-eyebrow-label {
      font-size: 0.77rem;
      font-weight: 700;
      color: var(--cyan);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      text-align: center;
      margin-bottom: 12px;
    }
    .so-h2 {
      font-size: clamp(1.6rem, 3vw, 2.4rem);
      font-weight: 800;
      color: var(--text-main);
      text-align: center;
      letter-spacing: -0.03em;
      line-height: 1.15;
      margin-bottom: 12px;
    }
    .so-section-sub {
      font-size: 1rem;
      color: var(--text-muted);
      text-align: center;
      max-width: 520px;
      margin: 0 auto 48px;
      line-height: 1.65;
    }

    /* ── Feature Cards ── */
    .so-feat-card {
      background: var(--bg-card);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 24px;
      height: 100%;
      transition: border-color var(--transition), transform var(--transition), box-shadow var(--transition);
      cursor: default;
    }
    .so-feat-card:hover {
      border-color: var(--cyan);
      transform: translateY(-2px);
      box-shadow: var(--shadow-cyan);
    }
    .so-feat-tag {
      display: inline-block;
      background: rgba(123,47,190,0.18);
      color: var(--purple-light);
      border-radius: 4px;
      padding: 2px 9px;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      margin-bottom: 10px;
    }
    .so-feat-title {
      font-size: 0.97rem;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
      letter-spacing: -0.01em;
    }
    .so-feat-desc {
      font-size: 0.84rem;
      color: var(--text-muted);
      line-height: 1.65;
    }

    /* ── How It Works ── */
    .so-how-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 24px;
    }
    .so-how-step { text-align: center; padding: 28px 20px; }
    .so-how-num {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--cyan-dim);
      border: 2px solid var(--cyan);
      color: var(--cyan);
      font-size: 1.2rem;
      font-weight: 900;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 16px;
    }
    .so-how-title {
      font-size: 0.97rem;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
    }
    .so-how-desc { font-size: 0.85rem; color: var(--text-muted); line-height: 1.65; }

    /* ── Testimonials ── */
    .so-testimonial-card {
      background: var(--bg-card);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 24px;
    }
    .so-stars { color: var(--cyan); font-size: 0.9rem; margin-bottom: 12px; }
    .so-quote-text {
      font-size: 0.9rem;
      color: var(--text-main);
      line-height: 1.7;
      font-style: italic;
      margin-bottom: 16px;
    }
    .so-quote-author { font-size: 0.82rem; font-weight: 700; color: var(--cyan); }
    .so-quote-role { font-size: 0.78rem; color: var(--text-muted); margin-top: 2px; }

    /* ── Pricing ── */
    .so-pricing-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }
    .so-price-card {
      background: var(--bg-card);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 28px 20px;
      position: relative;
      transition: border-color var(--transition), box-shadow var(--transition);
    }
    .so-price-card.popular {
      border-color: var(--cyan);
      box-shadow: var(--shadow-cyan);
    }
    .so-price-badge {
      position: absolute;
      top: -12px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--cyan);
      color: #000;
      font-size: 0.7rem;
      font-weight: 800;
      padding: 3px 12px;
      border-radius: 100px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .so-price-name {
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 12px;
    }
    .so-price-amount { display: flex; align-items: baseline; gap: 2px; margin-bottom: 4px; }
    .so-price-dollar { font-size: 0.95rem; font-weight: 700; color: var(--text-muted); }
    .so-price-num {
      font-size: 2.4rem;
      font-weight: 900;
      color: var(--text-main);
      line-height: 1;
      letter-spacing: -0.04em;
    }
    .so-price-period { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 20px; }
    .so-price-divider { border: none; border-top: 1px solid var(--bg-border); margin: 16px 0; }
    .so-price-feat {
      display: flex;
      align-items: flex-start;
      gap: 7px;
      font-size: 0.83rem;
      color: #9AA4C0;
      margin: 7px 0;
      line-height: 1.4;
    }
    .so-check { color: var(--cyan); font-weight: 700; flex-shrink: 0; }

    /* ── FAQ ── */
    .so-faq-item {
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 20px 24px;
      margin-bottom: 10px;
      background: var(--bg-card);
      transition: border-color var(--transition);
    }
    .so-faq-item:hover { border-color: rgba(0,212,255,0.25); }
    .so-faq-q { font-size: 0.96rem; font-weight: 700; color: var(--text-main); margin-bottom: 8px; }
    .so-faq-a { font-size: 0.86rem; color: var(--text-muted); line-height: 1.7; }

    /* ── CTA ── */
    .so-cta-section {
      background: linear-gradient(135deg, rgba(0,212,255,0.07) 0%, rgba(123,47,190,0.05) 100%);
      border: 1px solid rgba(0,212,255,0.2);
      border-radius: var(--radius-xl);
      padding: 72px 40px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }
    .so-cta-section::before {
      content: '';
      position: absolute;
      top: -60px; left: 50%;
      transform: translateX(-50%);
      width: 600px; height: 300px;
      background: radial-gradient(ellipse, rgba(0,212,255,0.08) 0%, transparent 70%);
      pointer-events: none;
    }
    .so-cta-h2 {
      font-size: clamp(1.6rem, 3vw, 2.4rem);
      font-weight: 900;
      color: var(--text-main);
      letter-spacing: -0.03em;
      line-height: 1.15;
      margin-bottom: 14px;
    }
    .so-cta-sub {
      font-size: 1rem;
      color: var(--text-muted);
      max-width: 480px;
      margin: 0 auto 36px;
      line-height: 1.65;
    }

    /* ── Footer ── */
    .so-footer {
      border-top: 1px solid var(--bg-border);
      padding: 40px 0 24px;
      margin-top: 80px;
    }
    .so-footer-grid {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 40px;
      margin-bottom: 32px;
    }
    .so-footer-brand {
      font-size: 1.1rem;
      font-weight: 800;
      background: var(--grad-text);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 8px;
    }
    .so-footer-tagline { font-size: 0.84rem; color: var(--text-muted); line-height: 1.6; max-width: 280px; }
    .so-footer-col-title {
      font-size: 0.77rem;
      font-weight: 700;
      color: var(--text-main);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 12px;
    }
    .so-footer-link {
      display: block;
      font-size: 0.83rem;
      color: var(--text-muted);
      text-decoration: none;
      margin-bottom: 8px;
      transition: color var(--transition);
    }
    .so-footer-link:hover { color: var(--cyan); }
    .so-footer-bottom {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 20px;
      border-top: 1px solid var(--bg-border);
      font-size: 0.79rem;
      color: var(--text-dim);
      flex-wrap: wrap;
      gap: 8px;
    }
    .so-footer-bottom a { color: var(--cyan); text-decoration: none; }

    /* ── Buttons ── */
    .stButton > button[kind="primary"] {
      background: linear-gradient(135deg, #00D4FF, #7B2FBE) !important;
      color: #fff !important;
      border: none !important;
      font-weight: 800 !important;
      font-size: 0.97rem !important;
      padding: 14px 32px !important;
      border-radius: 10px !important;
      min-height: 52px !important;
      letter-spacing: -0.01em !important;
      box-shadow: 0 4px 28px rgba(0,212,255,0.2) !important;
      transition: all var(--transition) !important;
    }
    .stButton > button[kind="primary"]:hover {
      box-shadow: 0 6px 36px rgba(0,212,255,0.3) !important;
      transform: translateY(-1px);
    }
    .stButton > button:not([kind="primary"]) {
      background: transparent !important;
      border: 1px solid var(--bg-border) !important;
      color: var(--text-muted) !important;
      font-size: 0.9rem !important;
      padding: 12px 24px !important;
      border-radius: 10px !important;
      min-height: 46px !important;
      transition: all var(--transition) !important;
    }
    .stButton > button:not([kind="primary"]):hover {
      border-color: rgba(0,212,255,0.3) !important;
      color: var(--text-main) !important;
    }

    /* ── Responsive ── */
    @media (max-width: 1024px) {
      .so-pricing-grid { grid-template-columns: repeat(2, 1fr); }
      .so-footer-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 768px) {
      .block-container { padding: 0 1rem 4rem; }
      .so-hero { padding: 60px 12px 44px; }
      .so-stats { grid-template-columns: repeat(2, 1fr); }
      .so-how-grid { grid-template-columns: 1fr; }
      .so-pricing-grid { grid-template-columns: 1fr; }
      .so-footer-grid { grid-template-columns: 1fr; gap: 24px; }
      .so-footer-bottom { flex-direction: column; text-align: center; }
      .so-nav .so-nav-links { display: none; }
      .so-cta-section { padding: 48px 20px; }
    }
    @media (max-width: 480px) {
      .so-stats { grid-template-columns: 1fr 1fr; }
      .so-h1 { font-size: 2rem; }
      .so-h2 { font-size: 1.5rem; }
    }
    </style>
    """)

    # ── TOP NAV ───────────────────────────────────────────────────────────────
    st.markdown("""
    <nav class="so-nav" role="navigation" aria-label="Main navigation">
      <a class="so-nav-brand" href="/" aria-label="SoleOps Home">👟 SoleOps</a>
      <div class="so-nav-links">
        <a class="so-nav-link" href="#features">Features</a>
        <a class="so-nav-link" href="#how-it-works">How It Works</a>
        <a class="so-nav-link" href="#pricing">Pricing</a>
        <a class="so-nav-link" href="#faq">FAQ</a>
      </div>
    </nav>
    """, unsafe_allow_html=True)

    # ── HERO ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <header class="so-hero" role="banner">
      <div class="so-eyebrow">👟 Built by a reseller, for resellers · eBay + Mercari + AI</div>
      <h1 class="so-h1">
        Stop Leaving Money<br><span>on the Table.</span>
      </h1>
      <p class="so-hero-sub">
        SoleOps is the all-in-one operations platform for serious sneaker resellers.
        Real-time price alerts, AI-generated listings, P&amp;L tracking, and arbitrage
        scanning — everything you need to run a tighter operation.
      </p>
    </header>
    """, unsafe_allow_html=True)

    hero_l, hero_c, hero_r = st.columns([1, 2, 1])
    with hero_c:
        if st.button("👟 Start Free — No Credit Card", type="primary", use_container_width=True):
            st.switch_page("app.py")
        st.markdown("""
        <div class="so-trust">
          <span class="so-trust-item"><span class="so-trust-check">✓</span> Free tier forever</span>
          <span class="so-trust-item"><span class="so-trust-check">✓</span> No credit card</span>
          <span class="so-trust-item"><span class="so-trust-check">✓</span> Cancel anytime</span>
          <span class="so-trust-item"><span class="so-trust-check">✓</span> Real data, real comps</span>
        </div>
        """, unsafe_allow_html=True)

    # ── STATS ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="so-stats" role="region" aria-label="Key statistics">
      <div class="so-stat">
        <div class="so-stat-num">Real-Time</div>
        <div class="so-stat-label">eBay + Mercari Prices</div>
      </div>
      <div class="so-stat">
        <div class="so-stat-num">AI</div>
        <div class="so-stat-label">Listing Generator</div>
      </div>
      <div class="so-stat">
        <div class="so-stat-num">$0</div>
        <div class="so-stat-label">To Start</div>
      </div>
      <div class="so-stat">
        <div class="so-stat-num">8+</div>
        <div class="so-stat-label">Reseller Tools</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CAROUSEL CSS + SHOE PRODUCT CAROUSEL ─────────────────────────────────
    _heat_listings = _load_ebay_listings(1)  # Load real inventory for carousel
    st.html(CAROUSEL_BASE_CSS + carousel_theme_css("cyan"))
    st.markdown(f"""
<div class="carousel-section">
  <div class="carousel-section-header">
    <span class="carousel-eyebrow" style="color:#00D4FF;">The Heat Right Now</span>
    <h2 class="carousel-title">Built for the Culture</h2>
    <p class="carousel-subtitle">
      Real sneakers. Real resellers. Real numbers. SoleOps is built by
      someone who actually flips — not a tech bro who read a blog post.
    </p>
    <a href="https://www.ebay.com/sch/i.html?_nkw=sneakers&LH_BIN=1&_sop=15" target="_blank"
       rel="noopener noreferrer"
       style="display:inline-block;margin-top:14px;padding:11px 26px;background:linear-gradient(90deg,#00D4FF,#7B2FBE);border-radius:8px;color:#fff;font-weight:700;font-size:0.9rem;text-decoration:none;letter-spacing:0.04em;box-shadow:0 4px 18px rgba(0,212,255,0.35);">
      🛒 Shop My eBay Listings ↗
    </a>
  </div>
  {render_shoe_product_carousel("cyan", db_listings=_heat_listings)}
  <div style="margin-top:20px;"></div>
  {render_story_band_html(
    "I built SoleOps between inventory runs. Every feature exists because I personally needed it — "
    "and couldn't find anything else that actually worked for sneaker resellers.",
    "Darrian Belcher · Builder · Reseller · Atlanta, GA",
    "#00D4FF"
  )}
</div>
""", unsafe_allow_html=True)

    # ── FEATURES ──────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="so-section" id="features" aria-label="Features">
      <div class="so-eyebrow-label">Features</div>
      <h2 class="so-h2">Every Tool You Need to Run a Tighter Resale Operation</h2>
      <p class="so-section-sub">From real-time alerts to AI copywriting — SoleOps handles the operational work so you can focus on flipping.</p>
    </section>
    """, unsafe_allow_html=True)

    features = [
        ("⚡ Real-Time", "📈 Price Monitor", "Live eBay and Mercari sold comps for every SKU in your inventory. Telegram alerts fire the moment a price drops below your sell target — or a deal hits below your buy threshold."),
        ("🤖 AI-Powered", "✍️ AI Listing Generator", "Claude AI writes keyword-optimized eBay titles and Mercari descriptions in seconds. Better copy = more views = faster sales = higher sell-through rates."),
        ("📊 Analytics", "💰 P&L Dashboard", "Per-pair net profit after eBay (13.25%) and Mercari (10%) fees. Monthly trends, best/worst performers, and a Schedule C tax summary for self-employment reporting."),
        ("🔍 Scanner", "🔍 Arbitrage Scanner", "Add target pairs to your watchlist with a max buy price. SoleOps scans Mercari continuously and fires a Telegram alert the moment a listing appears below your threshold."),
        ("⚠️ AI Strategy", "⚠️ Stale Inventory AI", "Flag pairs sitting unsold past 30/60/90 days. Claude recommends exact markdown amounts and cross-listing strategies per pair — stop holding dead inventory."),
        ("📦 Management", "📦 Inventory Manager", "Full CRUD inventory with SKU, size, COGS, condition, date purchased, date listed, and platform. Everything you need for taxes, profit tracking, and cash flow visibility."),
    ]

    f_rows = [features[i:i+3] for i in range(0, len(features), 3)]
    for row in f_rows:
        cols = st.columns(3, gap="medium")
        for col, (tag, title, desc) in zip(cols, row):
            with col:
                st.markdown(f"""
                <article class="so-feat-card">
                  <span class="so-feat-tag">{tag}</span>
                  <h3 class="so-feat-title">{title}</h3>
                  <p class="so-feat-desc">{desc}</p>
                </article>
                """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── HOW IT WORKS ──────────────────────────────────────────────────────────
    st.markdown("""
    <section class="so-section" id="how-it-works" aria-label="How SoleOps works">
      <div class="so-eyebrow-label">How It Works</div>
      <h2 class="so-h2">From Signup to Your First Alert in Under 10 Minutes</h2>
      <p class="so-section-sub">No complicated setup. No API keys to configure. Just add your inventory and let SoleOps work for you.</p>
      <div class="so-how-grid">
        <div class="so-how-step">
          <div class="so-how-num" aria-hidden="true">1</div>
          <h3 class="so-how-title">Create Your Free Account</h3>
          <p class="so-how-desc">Sign up in 30 seconds. No credit card required. The free tier includes 5 inventory items, manual price lookup, and basic P&L — enough to see the value immediately.</p>
        </div>
        <div class="so-how-step">
          <div class="so-how-num" aria-hidden="true">2</div>
          <h3 class="so-how-title">Add Your Inventory</h3>
          <p class="so-how-desc">Enter your pairs with SKU, size, COGS, and condition. SoleOps starts tracking comps immediately. Connect Telegram to receive real-time price alerts on your phone.</p>
        </div>
        <div class="so-how-step">
          <div class="so-how-num" aria-hidden="true">3</div>
          <h3 class="so-how-title">Flip Smarter</h3>
          <p class="so-how-desc">Use the arbitrage scanner to find deals below your buy price, the AI listing generator to write better copy, and the P&L dashboard to know exactly what you're making per pair.</p>
        </div>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── TESTIMONIALS ──────────────────────────────────────────────────────────
    st.markdown("""
    <section class="so-section" aria-label="Reseller testimonials">
      <div class="so-eyebrow-label">Results</div>
      <h2 class="so-h2">Resellers Who Run a Tighter Operation</h2>
      <p class="so-section-sub">Real resellers, real results — SoleOps users move faster, price smarter, and make more per flip.</p>
    </section>
    """, unsafe_allow_html=True)

    t1, t2, t3 = st.columns(3, gap="medium")
    testimonials = [
        ("★★★★★", "\"The arb scanner alone paid for the Pro plan in the first week. Caught a DS pair of Travis Scotts on Mercari $140 below my threshold. Flipped same day for $280 net.\"", "DeSean W.", "Full-time reseller, Atlanta GA"),
        ("★★★★★", "\"The AI listing generator changed my eBay game. My impressions went up 34% the first month just from better titles. I should have been using this from day one.\"", "Marcus O.", "Part-time reseller, Charlotte NC"),
        ("★★★★★", "\"I had 11 pairs sitting 60+ days. The stale inventory AI told me exactly what to drop each one to and where to cross-list. Cleared the whole lot in 3 weeks.\"", "Janelle T.", "Weekend reseller, Houston TX"),
    ]
    for col, (stars, quote, author, role) in zip([t1, t2, t3], testimonials):
        with col:
            st.markdown(f"""
            <article class="so-testimonial-card" itemscope itemtype="https://schema.org/Review">
              <div class="so-stars" aria-label="5 out of 5 stars">{stars}</div>
              <p class="so-quote-text" itemprop="reviewBody">{quote}</p>
              <div class="so-quote-author" itemprop="author">{author}</div>
              <div class="so-quote-role">{role}</div>
            </article>
            """, unsafe_allow_html=True)

    # ── PRICING ───────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="so-section" id="pricing" aria-label="Pricing">
      <div class="so-eyebrow-label">Pricing</div>
      <h2 class="so-h2">Simple Pricing for Every Reseller</h2>
      <p class="so-section-sub">Start free. Scale up as your operation grows. Cancel anytime — no lock-in, no questions.</p>
      <div class="so-pricing-grid">
        <div class="so-price-card">
          <div class="so-price-name">Free</div>
          <div class="so-price-amount">
            <span class="so-price-dollar">$</span>
            <span class="so-price-num">0</span>
          </div>
          <div class="so-price-period">forever · no credit card</div>
          <hr class="so-price-divider">
          <div class="so-price-feat"><span class="so-check">✓</span> 5 inventory items</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Manual price lookup</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Basic P&amp;L view</div>
        </div>
        <div class="so-price-card">
          <div class="so-price-name">Starter</div>
          <div class="so-price-amount">
            <span class="so-price-dollar">$</span>
            <span class="so-price-num">9.99</span>
          </div>
          <div class="so-price-period">per month · cancel anytime</div>
          <hr class="so-price-divider">
          <div class="so-price-feat"><span class="so-check">✓</span> 50 inventory items</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Telegram price alerts</div>
          <div class="so-price-feat"><span class="so-check">✓</span> AI listing generator</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Full P&amp;L dashboard</div>
        </div>
        <div class="so-price-card popular">
          <div class="so-price-badge">Most Popular</div>
          <div class="so-price-name">Pro ⭐</div>
          <div class="so-price-amount">
            <span class="so-price-dollar">$</span>
            <span class="so-price-num">19.99</span>
          </div>
          <div class="so-price-period">per month · cancel anytime</div>
          <hr class="so-price-divider">
          <div class="so-price-feat"><span class="so-check">✓</span> Unlimited inventory</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Arbitrage scanner</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Stale inventory AI</div>
          <div class="so-price-feat"><span class="so-check">✓</span> AI price advisor</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Schedule C export</div>
        </div>
        <div class="so-price-card">
          <div class="so-price-name">Pro+</div>
          <div class="so-price-amount">
            <span class="so-price-dollar">$</span>
            <span class="so-price-num">29.99</span>
          </div>
          <div class="so-price-period">per month · cancel anytime</div>
          <hr class="so-price-divider">
          <div class="so-price-feat"><span class="so-check">✓</span> Everything in Pro</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Direct API listing</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Multi-user access</div>
          <div class="so-price-feat"><span class="so-check">✓</span> Priority support</div>
        </div>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── FAQ ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="so-section" id="faq" aria-label="Frequently asked questions">
      <div class="so-eyebrow-label">FAQ</div>
      <h2 class="so-h2">Frequently Asked Questions</h2>
      <p class="so-section-sub">Everything you need to know before you sign up.</p>

      <div class="so-faq-item">
        <h3 class="so-faq-q">Is SoleOps free to use?</h3>
        <p class="so-faq-a">Yes. The free tier includes 5 inventory items, manual price lookup, and basic P&L — no credit card required. Paid plans start at $9.99/month for Telegram alerts, AI listings, and 50 inventory slots.</p>
      </div>
      <div class="so-faq-item">
        <h3 class="so-faq-q">How do the real-time eBay and Mercari price alerts work?</h3>
        <p class="so-faq-a">SoleOps monitors eBay sold listings and Mercari active listings for your tracked SKUs. When a comp drops below your sell target, or a target pair drops below your buy threshold, you get an instant Telegram notification on your phone.</p>
      </div>
      <div class="so-faq-item">
        <h3 class="so-faq-q">What platforms does the AI listing generator support?</h3>
        <p class="so-faq-a">The AI listing generator (powered by Anthropic Claude) creates keyword-optimized titles and descriptions for both eBay and Mercari. Better titles rank higher in platform search, get more clicks, and sell faster.</p>
      </div>
      <div class="so-faq-item">
        <h3 class="so-faq-q">How does the arbitrage scanner find deals?</h3>
        <p class="so-faq-a">Add pairs to your watchlist with a maximum buy price. SoleOps continuously scans Mercari for those SKUs and fires a Telegram alert the moment a listing appears below your threshold. You're first to know, first to buy.</p>
      </div>
      <div class="so-faq-item">
        <h3 class="so-faq-q">Does SoleOps help with taxes for resellers?</h3>
        <p class="so-faq-a">Yes. The P&L dashboard tracks per-pair net profit after eBay (13.25%) and Mercari (10%) fees automatically. Pro plan includes a Schedule C tax summary — the exact format your accountant or tax software needs for self-employment income.</p>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── FINAL CTA ─────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="so-cta-section" aria-label="Call to action">
      <h2 class="so-cta-h2">Ready to Run a Tighter Resale Operation?</h2>
      <p class="so-cta-sub">
        Start free. No credit card. Cancel anytime.<br>
        Your inventory data stays yours — always.
      </p>
    </section>
    """, unsafe_allow_html=True)

    cta_l, cta_c, cta_r = st.columns([1, 2, 1])
    with cta_c:
        st.markdown("<div style='margin-top:-24px;'></div>", unsafe_allow_html=True)
        if st.button("👟 Start Free Now", type="primary", use_container_width=True, key="cta_bottom"):
            st.switch_page("app.py")
        st.markdown("<div style='text-align:center; color:#7A80A0; font-size:0.78rem; margin-top:8px;'>No credit card · Free tier forever · Cancel paid plans anytime</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("Already have an account? Sign In →", use_container_width=True, key="signin_bottom"):
            st.switch_page("app.py")

    # ── FOOTER ────────────────────────────────────────────────────────────────
    st.markdown("""
    <footer class="so-footer" role="contentinfo">
      <div class="so-footer-grid">
        <div>
          <div class="so-footer-brand">👟 SoleOps</div>
          <p class="so-footer-tagline">Sneaker reseller operations platform. Real-time price alerts, AI listings, P&L tracking, and arbitrage scanning — built by a reseller, for resellers.</p>
        </div>
        <div>
          <div class="so-footer-col-title">Product</div>
          <span class="so-footer-link">Features</span>
          <span class="so-footer-link">Pricing</span>
          <span class="so-footer-link">FAQ</span>
        </div>
        <div>
          <div class="so-footer-col-title">Connect</div>
          <a class="so-footer-link" href="https://www.linkedin.com/in/darrian-belcher/" rel="noopener noreferrer" target="_blank">LinkedIn</a>
          <a class="so-footer-link" href="https://getsoleops.com" rel="noopener noreferrer" target="_blank">getsoleops.com</a>
        </div>
      </div>
      <div class="so-footer-bottom">
        <span>© 2026 SoleOps · Sneaker Reseller Operations Platform · Built by <a href="https://www.linkedin.com/in/darrian-belcher/" rel="noopener noreferrer" target="_blank">Darrian Belcher</a></span>
        <span>eBay price alerts · Mercari scanner · AI listing generator · P&amp;L tracker</span>
      </div>
    </footer>
    """, unsafe_allow_html=True)

    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATED DASHBOARD — shown to logged-in users
# ═══════════════════════════════════════════════════════════════════════════════
uid = user.get("id", 0)
username = user.get("username", "Reseller")


# ── eBay Live Inventory Banner helpers ────────────────────────────────────────
import json as _json
import urllib.parse as _urlparse

def _load_ebay_listings(user_id: int) -> list[dict]:
    """
    Pull all inventory items that are listed on eBay.
    Supports both the legacy `sneaker_inventory` and the newer `soleops_inventory` tables.
    Returns list of dicts: {brand, model, size, price, ebay_url, colorway, sku}
    """
    results = []
    try:
        conn = get_conn()
        cur = conn.cursor()

        # ── Try soleops_inventory (118_soleops_inventory_manager.py schema) ──
        try:
            cur.execute("""
                SELECT brand, model, colorway, size, sku, listed_platforms, list_prices
                FROM soleops_inventory
                WHERE user_id = ? AND status IN ('listed', 'in_stock')
            """, (user_id,))
            for row in cur.fetchall():
                brand, model, colorway, size, sku, platforms_raw, prices_raw = row
                try:
                    platforms = _json.loads(platforms_raw) if isinstance(platforms_raw, str) else (platforms_raw or [])
                    prices    = _json.loads(prices_raw)    if isinstance(prices_raw, str)    else (prices_raw or {})
                except Exception:
                    platforms, prices = [], {}

                # Only include items listed on eBay
                listed_on_ebay = any("ebay" in str(p).lower() for p in platforms)
                if not listed_on_ebay and platforms:
                    # still show all listed items if eBay not set — show all
                    pass

                price = prices.get("eBay") or prices.get("ebay") or prices.get("StockX") or None
                query = f"{brand} {model} {f'Size {size}' if size else ''}".strip()
                if sku:
                    query = sku
                ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={_urlparse.quote_plus(query)}&LH_Sold=0&LH_BIN=1"
                results.append({
                    "brand": brand or "",
                    "model": model or "",
                    "colorway": colorway or "",
                    "size": size or "?",
                    "sku": sku or "",
                    "price": float(price) if price else None,
                    "ebay_url": ebay_url,
                })
        except Exception:
            pass  # table may not exist yet

        # ── Try sneaker_inventory (older dashboard schema) ──────────────────
        if not results:
            try:
                cur.execute("""
                    SELECT shoe_name, size, cost_basis, listed_price, listed_platform, sku
                    FROM sneaker_inventory
                    WHERE user_id = ? AND status = 'active'
                """, (user_id,))
                for row in cur.fetchall():
                    shoe_name, size, cost_basis, listed_price, platform, sku = row
                    query = f"{shoe_name} Size {size}".strip() if shoe_name else ""
                    if sku:
                        query = sku
                    ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={_urlparse.quote_plus(query)}&LH_BIN=1"
                    results.append({
                        "brand": "",
                        "model": shoe_name or "Unknown",
                        "colorway": "",
                        "size": str(size) if size else "?",
                        "sku": sku or "",
                        "price": float(listed_price) if listed_price else None,
                        "ebay_url": ebay_url,
                    })
            except Exception:
                pass

        conn.close()
    except Exception:
        pass
    return results


def _render_ebay_banner(listings: list[dict]) -> None:
    """
    Render a scrolling marquee banner showing all eBay-listed inventory.
    Each card shows: shoe name + colorway, size badge, price, and eBay link.
    """
    if not listings:
        st.markdown("""
        <div style="
          background: linear-gradient(90deg, rgba(0,212,255,0.05) 0%, rgba(123,47,190,0.05) 100%);
          border: 1px dashed rgba(0,212,255,0.25);
          border-radius: 12px;
          padding: 16px 24px;
          text-align: center;
          color: #7A80A0;
          font-size: 0.85rem;
          margin-bottom: 20px;
        ">
          📦 No eBay listings found yet — add inventory and mark items as listed to see them here.
        </div>
        """, unsafe_allow_html=True)
        return

    # Build card HTML for each listing
    cards_html = ""
    for item in listings:
        name_parts = [x for x in [item["brand"], item["model"]] if x]
        display_name = " ".join(name_parts) if name_parts else "Unknown Shoe"
        if item["colorway"]:
            display_name += f' <span style="color:#7A80A0;font-weight:400;">"{item["colorway"]}"</span>'
        price_html = f'<span class="so-banner-price">${item["price"]:,.0f}</span>' if item["price"] else ""
        cards_html += f"""
        <a class="so-banner-card" href="{item['ebay_url']}" target="_blank" rel="noopener noreferrer" title="View on eBay: {item.get('model','')} Size {item['size']}">
          <span class="so-banner-shoe-icon">👟</span>
          <span class="so-banner-name">{display_name}</span>
          <span class="so-banner-size">Sz {item['size']}</span>
          {price_html}
          <span class="so-banner-badge">eBay ↗</span>
        </a>
        """

    # Duplicate for seamless infinite scroll
    marquee_content = cards_html + cards_html

    count_label = f"{len(listings)} pair{'s' if len(listings) != 1 else ''} live on eBay"

    st.html(f"""
    <style>
    .so-ebay-banner-wrap {{
      position: relative;
      background: linear-gradient(135deg, rgba(0,212,255,0.06) 0%, rgba(123,47,190,0.04) 100%);
      border: 1px solid rgba(0,212,255,0.2);
      border-radius: 14px;
      overflow: hidden;
      margin-bottom: 24px;
    }}
    .so-ebay-banner-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 20px 6px;
      border-bottom: 1px solid rgba(0,212,255,0.12);
    }}
    .so-ebay-banner-title {{
      font-size: 0.75rem;
      font-weight: 800;
      color: #00D4FF;
      text-transform: uppercase;
      letter-spacing: 0.09em;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .so-ebay-banner-count {{
      font-size: 0.72rem;
      color: #7A80A0;
      background: rgba(0,212,255,0.08);
      border: 1px solid rgba(0,212,255,0.18);
      padding: 2px 10px;
      border-radius: 100px;
    }}
    .so-ebay-marquee-track {{
      display: flex;
      overflow: hidden;
      padding: 10px 0 12px;
      gap: 0;
    }}
    .so-ebay-marquee-inner {{
      display: flex;
      gap: 10px;
      animation: soBannerScroll 30s linear infinite;
      white-space: nowrap;
      padding: 0 10px;
      flex-shrink: 0;
    }}
    .so-ebay-marquee-inner:hover {{ animation-play-state: paused; }}
    @keyframes soBannerScroll {{
      0%   {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}
    .so-banner-card {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(14,16,34,0.85);
      border: 1px solid rgba(0,212,255,0.18);
      border-radius: 10px;
      padding: 8px 14px;
      text-decoration: none;
      color: #F0F4FF;
      font-size: 0.83rem;
      font-weight: 500;
      transition: border-color 0.2s, background 0.2s, transform 0.15s;
      flex-shrink: 0;
      max-width: 340px;
      cursor: pointer;
    }}
    .so-banner-card:hover {{
      border-color: #00D4FF;
      background: rgba(0,212,255,0.1);
      transform: translateY(-1px);
      box-shadow: 0 4px 20px rgba(0,212,255,0.15);
      color: #F0F4FF;
      text-decoration: none;
    }}
    .so-banner-shoe-icon {{ font-size: 1rem; flex-shrink: 0; }}
    .so-banner-name {{
      font-weight: 600;
      color: #E8EEFF;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 180px;
    }}
    .so-banner-size {{
      background: rgba(0,212,255,0.12);
      border: 1px solid rgba(0,212,255,0.25);
      color: #00D4FF;
      font-size: 0.7rem;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 6px;
      flex-shrink: 0;
      letter-spacing: 0.03em;
    }}
    .so-banner-price {{
      color: #22D47E;
      font-weight: 700;
      font-size: 0.82rem;
      flex-shrink: 0;
    }}
    .so-banner-badge {{
      background: rgba(0,212,255,0.15);
      color: #00D4FF;
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 4px;
      flex-shrink: 0;
      letter-spacing: 0.04em;
    }}
    /* Fade edges */
    .so-ebay-banner-wrap::before,
    .so-ebay-banner-wrap::after {{
      content: '';
      position: absolute;
      top: 0; bottom: 0; width: 60px;
      z-index: 2;
      pointer-events: none;
    }}
    .so-ebay-banner-wrap::before {{
      left: 0;
      background: linear-gradient(to right, rgba(6,8,15,0.95) 0%, transparent 100%);
    }}
    .so-ebay-banner-wrap::after {{
      right: 0;
      background: linear-gradient(to left, rgba(6,8,15,0.95) 0%, transparent 100%);
    }}
    </style>

    <div class="so-ebay-banner-wrap" role="region" aria-label="Live eBay inventory">
      <div class="so-ebay-banner-header">
        <span class="so-ebay-banner-title">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0">
            <circle cx="5" cy="5" r="5" fill="#00D4FF" opacity="0.25"/>
            <circle cx="5" cy="5" r="2.5" fill="#00D4FF">
              <animate attributeName="r" values="2.5;4;2.5" dur="1.5s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="1;0.3;1" dur="1.5s" repeatCount="indefinite"/>
            </circle>
          </svg>
          Live eBay Inventory
        </span>
        <span class="so-ebay-banner-count">{count_label}</span>
      </div>
      <div class="so-ebay-marquee-track">
        <div class="so-ebay-marquee-inner">
          {marquee_content}
        </div>
      </div>
    </div>
    """)

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("soleops_app.py",                          label="🏠 Dashboard",           icon="🏠")
st.sidebar.page_link("pages/65_sneaker_inventory_analyzer.py",  label="📦 Inventory Analyzer",  icon="📦")
st.sidebar.page_link("pages/68_soleops_price_monitor.py",       label="📈 Price Monitor",        icon="📈")
st.sidebar.page_link("pages/69_soleops_pnl_dashboard.py",       label="💰 P&L Dashboard",        icon="💰")
st.sidebar.page_link("pages/71_soleops_arb_scanner.py",         label="🔍 Arb Scanner",          icon="🔍")
st.sidebar.page_link("pages/72_resale_price_advisor.py",        label="🤖 AI Price Advisor",     icon="🤖")
st.sidebar.page_link("pages/84_soleops_stale_inventory.py",     label="⚠️ Stale Inventory",      icon="⚠️")
st.sidebar.page_link("pages/85_soleops_inventory_manager.py",   label="🗂️ Inventory Manager",    icon="🗂️")
st.sidebar.page_link("pages/86_soleops_listing_generator.py",   label="✍️ Listing Generator",    icon="✍️")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/70_soleops_stripe_paywall.py",      label="💳 Subscription",         icon="💳")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/146_immich_photo_manager.py",        label="Photo Library",           icon="📸")
render_sidebar_user_widget()

st.title("👟 SoleOps")
st.markdown(f"Welcome back, **{username}** — your sneaker resale command center.")

# ── Live eBay Inventory Banner ─────────────────────────────────────────────────
ebay_listings = _load_ebay_listings(uid)
_render_ebay_banner(ebay_listings)

st.markdown("---")

# ── Quick Stats ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

inv_count = total_pnl = stale_count = alerts_count = None
try:
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM sneaker_inventory WHERE user_id = ? AND status = 'active'", (uid,))
        row = cursor.fetchone()
        inv_count = row[0] if row else 0
    except Exception:
        pass
    try:
        cursor.execute("SELECT COALESCE(SUM(net_profit), 0) FROM sneaker_inventory WHERE user_id = ? AND status = 'sold'", (uid,))
        row = cursor.fetchone()
        total_pnl = row[0] if row else 0
    except Exception:
        pass
    try:
        cursor.execute("""SELECT COUNT(*) FROM sneaker_inventory WHERE user_id = ? AND status = 'active'
               AND date_listed IS NOT NULL AND julianday('now') - julianday(date_listed) > 30""", (uid,))
        row = cursor.fetchone()
        stale_count = row[0] if row else 0
    except Exception:
        pass
    try:
        cursor.execute("SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_active = 1", (uid,))
        row = cursor.fetchone()
        alerts_count = row[0] if row else 0
    except Exception:
        pass
    conn.close()
except Exception:
    pass

with col1:
    st.metric("📦 Active Inventory", f"{inv_count}" if inv_count is not None else "—", help="Pairs currently listed or in hand")
with col2:
    st.metric("💰 Total Net Profit", f"${total_pnl:,.2f}" if total_pnl is not None else "—", help="Net profit across all sold pairs")
with col3:
    st.metric("⚠️ Stale Pairs", f"{stale_count}" if stale_count is not None else "—",
              delta=f"-{stale_count} need action" if stale_count else None,
              delta_color="inverse" if stale_count else "off",
              help="Pairs unsold 30+ days")
with col4:
    st.metric("🔔 Price Alerts", f"{alerts_count}" if alerts_count is not None else "—", help="Active eBay/Mercari monitors")

st.markdown("---")
st.subheader("🚀 Your Tools")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 📈 Price Monitor")
    st.markdown("Real-time eBay + Mercari prices with Telegram alerts.")
    if st.button("Open Price Monitor →", key="btn_price"):
        st.switch_page("pages/68_soleops_price_monitor.py")
with c2:
    st.markdown("#### 💰 P&L Dashboard")
    st.markdown("Per-pair profit after fees. Monthly trends. Schedule C.")
    if st.button("Open P&L Dashboard →", key="btn_pnl"):
        st.switch_page("pages/69_soleops_pnl_dashboard.py")
with c3:
    st.markdown("#### ✍️ AI Listing Generator")
    st.markdown("Claude-powered eBay + Mercari titles and descriptions.")
    if st.button("Open Listing Generator →", key="btn_listing"):
        st.switch_page("pages/86_soleops_listing_generator.py")

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("#### 🔍 Arbitrage Scanner")
    st.markdown("Watchlist + Telegram alert when target pairs go below buy price.")
    if st.button("Open Arb Scanner →", key="btn_arb"):
        st.switch_page("pages/71_soleops_arb_scanner.py")
with c5:
    st.markdown("#### ⚠️ Stale Inventory")
    st.markdown("Flag aging pairs. AI markdown strategy per pair.")
    if st.button("Open Stale Inventory →", key="btn_stale"):
        st.switch_page("pages/84_soleops_stale_inventory.py")
with c6:
    st.markdown("#### 🤖 AI Price Advisor")
    st.markdown("Claude recommends optimal list price vs current comps.")
    if st.button("Open Price Advisor →", key="btn_advisor"):
        st.switch_page("pages/72_resale_price_advisor.py")

st.markdown("---")
st.caption("SoleOps — Built for serious sneaker resellers | Powered by Claude AI + Real-Time Market Data")
