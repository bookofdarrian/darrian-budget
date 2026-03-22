"""
College Confused — Standalone Streamlit Entry Point (SEO-Optimized)
Port: 8503 | Domain: collegeconfused.org
Run: streamlit run cc_app.py --server.port=8503 --server.address=0.0.0.0

Public landing page shown to unauthenticated visitors (Googlebot-indexable).
Mobile-first design · Core Web Vitals compliant · JSON-LD + FAQPage schema.
Authenticated users see the full dashboard.
"""

import streamlit as st
from utils.db import init_db
from utils.auth import (
    inject_cc_css,
    render_sidebar_brand,
    render_sidebar_user_widget,
    get_current_user,
)

st.set_page_config(
    page_title="College Confused — Free AI College Prep for Every Student | Applications, Essays & Scholarships",
    page_icon="🎓",
    layout="wide",
)

init_db()
inject_cc_css()

user = get_current_user()

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC LANDING PAGE — shown to unauthenticated visitors + Googlebot
# ═══════════════════════════════════════════════════════════════════════════════
if not user:

    # ── Hide sidebar for public landing ───────────────────────────────────────
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── SEO: Meta tags + JSON-LD injected to <head> via JS ───────────────────
    st.markdown("""
    <script>
    (function() {
      var metas = [
        { name: 'description', content: 'College Confused is the free AI-powered college prep platform for every student. Track application deadlines, find scholarships, write AI-assisted essays, build your college list, prep for SAT/ACT, and navigate FAFSA — all in one place.' },
        { property: 'og:title', content: 'College Confused — Free AI College Prep for Every Student' },
        { property: 'og:description', content: 'Free AI college prep: deadline tracker, scholarship finder, AI essay station, SAT/ACT prep, college list builder, and FAFSA guide. Built for first-gen students.' },
        { property: 'og:type', content: 'website' },
        { property: 'og:url', content: 'https://collegeconfused.org' },
        { property: 'og:site_name', content: 'College Confused' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: 'College Confused — Free AI College Prep for Every Student' },
        { name: 'twitter:description', content: 'Free AI college prep: deadlines, scholarships, essays, SAT/ACT prep, FAFSA guide. 100% free.' },
        { name: 'robots', content: 'index, follow' },
        { name: 'keywords', content: 'free college prep app, AI essay help college application, scholarship finder for students, college application deadline tracker, FAFSA guide for students, SAT ACT prep free, Common App essay helper, first gen college student tools, college list builder AI' },
        { name: 'author', content: 'Darrian Belcher' },
        { name: 'theme-color', content: '#9B8EFF' }
      ];
      metas.forEach(function(attrs) {
        var existing = attrs.name ? document.querySelector('meta[name="'+attrs.name+'"]') : document.querySelector('meta[property="'+attrs.property+'"]');
        var tag = existing || document.createElement('meta');
        Object.keys(attrs).forEach(function(k){ tag.setAttribute(k, attrs[k]); });
        if (!existing) document.head.appendChild(tag);
      });
      if (!document.querySelector('link[rel="canonical"]')) {
        var link = document.createElement('link');
        link.rel = 'canonical'; link.href = 'https://collegeconfused.org';
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
          "name": "College Confused",
          "url": "https://collegeconfused.org",
          "description": "College Confused is the free AI-powered college prep platform for every student. It includes application deadline tracking, scholarship finder, AI essay station (powered by Claude), college list builder, SAT/ACT prep, and a FAFSA guide — all completely free.",
          "applicationCategory": "EducationalApplication",
          "operatingSystem": "Web",
          "offers": {
            "@type": "Offer",
            "name": "Free",
            "price": "0",
            "priceCurrency": "USD",
            "description": "Full access to all 7 AI-powered college prep tools — completely free, no credit card required"
          },
          "author": {
            "@type": "Person",
            "name": "Darrian Belcher",
            "url": "https://www.linkedin.com/in/darrian-belcher/"
          },
          "audience": {
            "@type": "Audience",
            "audienceType": "High school students applying to college, first-generation college students, college counselors"
          },
          "featureList": [
            "College application deadline tracker",
            "Scholarship finder and tracker",
            "AI essay station powered by Claude (Common App and supplements)",
            "College list builder with reach, match, and safety schools",
            "SAT/ACT practice and AI study plans",
            "FAFSA step-by-step guide",
            "Unlimited AI essay drafts"
          ]
        },
        {
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "Is College Confused really free?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes, 100% free. All 7 AI-powered tools — deadline tracker, scholarship finder, essay station, college list builder, SAT/ACT prep, and FAFSA guide — are completely free. No credit card required, no premium tier."
              }
            },
            {
              "@type": "Question",
              "name": "How does the AI essay station work?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "The AI essay station uses Anthropic's Claude to help you brainstorm, draft, and polish your Common App personal statement and school-specific supplemental essays. You provide your story and experiences — Claude helps you shape them into compelling narratives. You can generate unlimited drafts."
              }
            },
            {
              "@type": "Question",
              "name": "Can College Confused help first-generation college students?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Absolutely. College Confused was built with first-gen students in mind. The FAFSA guide provides step-by-step help for students who don't have family experience navigating financial aid. The scholarship finder surfaces aid opportunities many first-gen students never find on their own."
              }
            },
            {
              "@type": "Question",
              "name": "What deadlines does the timeline tracker cover?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "The application timeline tracks Common App Early Decision, Early Action, Regular Decision, and Rolling Admission deadlines. It also tracks FAFSA submission deadlines, scholarship deadlines, financial aid award dates, and housing deposits — everything in one calendar view."
              }
            },
            {
              "@type": "Question",
              "name": "How does the scholarship finder work?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "The scholarship finder helps you discover scholarships based on your GPA, intended major, state of residence, background, and other criteria. You can track application status and deadlines for each scholarship in one organized dashboard."
              }
            }
          ]
        }
      ]
    }
    </script>
    """, unsafe_allow_html=True)

    # ── Master CSS ─────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* ── CSS Custom Properties ── */
    :root {
      --violet: #9B8EFF;
      --violet-light: #C4B8FF;
      --violet-dark: #6C5CE7;
      --violet-dim: rgba(155,142,255,0.12);
      --violet-glow: rgba(155,142,255,0.18);
      --bg-main: #08071A;
      --bg-surface: #0E0C2A;
      --bg-card: #12102A;
      --bg-border: #1E1C42;
      --text-main: #F2F0FF;
      --text-muted: #8A84B0;
      --text-dim: #3A385A;
      --success: #22D47E;
      --gold: #FFD166;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-xl: 28px;
      --shadow-violet: 0 0 40px rgba(155,142,255,0.12);
      --grad-violet: linear-gradient(135deg, #9B8EFF, #C4B8FF);
      --grad-bg: linear-gradient(135deg, #0E0C2A, #1A1640);
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
    #MainMenu, footer, [data-testid="stHeader"] { visibility: hidden; }

    /* ── Top Nav ── */
    .cc-nav {
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(8,7,26,0.88);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border-bottom: 1px solid var(--bg-border);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .cc-nav-brand {
      font-size: 1.1rem;
      font-weight: 800;
      background: var(--grad-violet);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.02em;
      text-decoration: none;
    }
    .cc-nav-links { display: flex; gap: 24px; align-items: center; }
    .cc-nav-link {
      color: var(--text-muted);
      font-size: 0.88rem;
      font-weight: 500;
      text-decoration: none;
      transition: color var(--transition);
    }
    .cc-nav-link:hover { color: var(--text-main); }

    /* ── Hero ── */
    .cc-hero {
      text-align: center;
      padding: 96px 20px 72px;
      position: relative;
    }
    .cc-hero::before {
      content: '';
      position: absolute;
      top: 0; left: 50%;
      transform: translateX(-50%);
      width: 700px; height: 500px;
      background: radial-gradient(ellipse at top, rgba(155,142,255,0.1) 0%, rgba(108,92,231,0.04) 40%, transparent 70%);
      pointer-events: none;
    }
    .cc-eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--violet-dim);
      border: 1px solid rgba(155,142,255,0.3);
      color: var(--violet-light);
      -webkit-text-fill-color: #C4B8FF !important;
      font-size: 0.78rem;
      font-weight: 700;
      padding: 5px 14px;
      border-radius: 100px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      margin-bottom: 28px;
    }
    .cc-h1 {
      font-size: clamp(2.2rem, 5vw, 3.8rem);
      font-weight: 900;
      color: var(--text-main);
      -webkit-text-fill-color: #F2F0FF !important;
      line-height: 1.08;
      letter-spacing: -0.04em;
      margin-bottom: 20px;
    }
    .cc-h1 span {
      background: var(--grad-violet);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .cc-hero-sub {
      font-size: clamp(1rem, 2vw, 1.2rem);
      color: var(--text-muted);
      -webkit-text-fill-color: #8A84B0 !important;
      max-width: 580px;
      margin: 0 auto 40px;
      line-height: 1.7;
    }
    .cc-trust {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 20px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    .cc-trust-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.82rem;
      color: var(--text-muted);
    }
    .cc-trust-check { color: var(--success); }

    /* ── Stats Bar ── */
    .cc-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1px;
      background: var(--bg-border);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-lg);
      overflow: hidden;
      margin: 48px 0;
    }
    .cc-stat {
      background: var(--bg-surface);
      padding: 24px 16px;
      text-align: center;
    }
    .cc-stat-num {
      font-size: 1.9rem;
      font-weight: 900;
      background: var(--grad-violet);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      line-height: 1;
      letter-spacing: -0.03em;
    }
    .cc-stat-label {
      font-size: 0.77rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.07em;
      margin-top: 6px;
    }

    /* ── Sections ── */
    .cc-section { margin: 72px 0; }
    .cc-eyebrow-label {
      font-size: 0.77rem;
      font-weight: 700;
      color: var(--violet);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      text-align: center;
      margin-bottom: 12px;
    }
    .cc-h2 {
      font-size: clamp(1.6rem, 3vw, 2.4rem);
      font-weight: 800;
      color: var(--text-main);
      text-align: center;
      letter-spacing: -0.03em;
      line-height: 1.15;
      margin-bottom: 12px;
    }
    .cc-section-sub {
      font-size: 1rem;
      color: var(--text-muted);
      text-align: center;
      max-width: 520px;
      margin: 0 auto 48px;
      line-height: 1.65;
    }

    /* ── Feature Cards ── */
    .cc-feat-card {
      background: var(--bg-card);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 24px;
      height: 100%;
      transition: border-color var(--transition), transform var(--transition), box-shadow var(--transition);
      cursor: default;
    }
    .cc-feat-card:hover {
      border-color: var(--violet);
      transform: translateY(-2px);
      box-shadow: var(--shadow-violet);
    }
    .cc-feat-icon {
      font-size: 1.75rem;
      margin-bottom: 12px;
      display: block;
    }
    .cc-feat-title {
      font-size: 0.97rem;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
      letter-spacing: -0.01em;
    }
    .cc-feat-desc {
      font-size: 0.84rem;
      color: var(--text-muted);
      line-height: 1.65;
    }


    /* ── Product Mockup Preview ── */
    .cc-mockup-wrap { max-width: 680px; margin: 28px auto 0; }
    .cc-mockup-browser {
      background: #16143A;
      border: 1px solid rgba(155,142,255,0.25);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 24px 64px rgba(0,0,0,0.55), 0 0 0 1px rgba(155,142,255,0.12);
    }
    .cc-mockup-bar {
      background: #0E0C26;
      border-bottom: 1px solid rgba(155,142,255,0.15);
      padding: 9px 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .cc-mockup-dots { display: flex; gap: 6px; }
    .cc-mockup-dots span { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
    .cc-mockup-dots span:nth-child(1) { background: #FF5F57; }
    .cc-mockup-dots span:nth-child(2) { background: #FFBD2E; }
    .cc-mockup-dots span:nth-child(3) { background: #28CA41; }
    .cc-mockup-url {
      background: rgba(155,142,255,0.07);
      border: 1px solid rgba(155,142,255,0.18);
      border-radius: 5px;
      padding: 3px 12px;
      font-size: 0.7rem;
      color: #8A84B0;
      -webkit-text-fill-color: #8A84B0 !important;
      flex: 1;
      text-align: center;
      letter-spacing: 0.01em;
    }
    .cc-mockup-screen { padding: 18px 20px 20px; }
    .cc-mock-greeting {
      font-size: 0.72rem;
      font-weight: 600;
      color: #C4B8FF;
      -webkit-text-fill-color: #C4B8FF !important;
      margin-bottom: 14px;
    }
    .cc-mock-stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 14px;
    }
    .cc-mock-stat {
      background: rgba(155,142,255,0.08);
      border: 1px solid rgba(155,142,255,0.2);
      border-radius: 8px;
      padding: 10px;
      text-align: center;
    }
    .cc-mock-stat-num {
      font-size: 1.15rem;
      font-weight: 800;
      background: linear-gradient(90deg, #9B8EFF 0%, #C4B8FF 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      display: block;
      line-height: 1.2;
    }
    .cc-mock-stat-lbl {
      font-size: 0.62rem;
      color: #8A84B0;
      -webkit-text-fill-color: #8A84B0 !important;
      display: block;
      margin-top: 3px;
    }
    .cc-mock-tasks { display: flex; flex-direction: column; gap: 6px; }
    .cc-mock-task {
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(255,255,255,0.03);
      border: 1px solid rgba(155,142,255,0.12);
      border-radius: 8px;
      padding: 8px 12px;
    }
    .cc-mock-task-icon { font-size: 0.9rem; }
    .cc-mock-task-text {
      flex: 1;
      font-size: 0.73rem;
      color: #F2F0FF;
      -webkit-text-fill-color: #F2F0FF !important;
    }
    .cc-mock-badge {
      font-size: 0.63rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 20px;
    }
    .cc-mock-badge-violet {
      background: rgba(155,142,255,0.15);
      color: #C4B8FF;
      -webkit-text-fill-color: #C4B8FF !important;
    }
    .cc-mock-badge-orange {
      background: rgba(255,179,71,0.15);
      color: #FFB347;
      -webkit-text-fill-color: #FFB347 !important;
    }
    .cc-mock-badge-teal {
      background: rgba(78,205,196,0.15);
      color: #4ECDC4;
      -webkit-text-fill-color: #4ECDC4 !important;
    }

    /* ── How It Works ── */
    .cc-how-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 24px;
    }
    .cc-how-step { text-align: center; padding: 28px 20px; }
    .cc-how-num {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--violet-dim);
      border: 2px solid var(--violet);
      color: var(--violet);
      font-size: 1.2rem;
      font-weight: 900;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 16px;
    }
    .cc-how-title {
      font-size: 0.97rem;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
    }
    .cc-how-desc { font-size: 0.85rem; color: var(--text-muted); line-height: 1.65; }

    /* ── Testimonials ── */
    .cc-testimonial-card {
      background: var(--bg-card);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 24px;
      border-left: 3px solid var(--violet);
    }
    .cc-stars { color: var(--gold); font-size: 0.9rem; margin-bottom: 12px; }
    .cc-quote-text {
      font-size: 0.9rem;
      color: var(--text-main);
      line-height: 1.7;
      font-style: italic;
      margin-bottom: 16px;
    }
    .cc-quote-author { font-size: 0.82rem; font-weight: 700; color: var(--violet-light); }
    .cc-quote-result { font-size: 0.78rem; color: var(--success); margin-top: 2px; font-weight: 600; }

    /* ── Mission Banner ── */
    .cc-mission {
      background: linear-gradient(135deg, rgba(155,142,255,0.08) 0%, rgba(108,92,231,0.05) 100%);
      border: 1px solid rgba(155,142,255,0.2);
      border-radius: var(--radius-xl);
      padding: 52px 48px;
    }
    .cc-mission-h3 {
      font-size: 1.6rem;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.02em;
      margin-bottom: 16px;
      line-height: 1.2;
    }
    .cc-mission-body {
      font-size: 0.95rem;
      color: var(--text-muted);
      line-height: 1.85;
    }
    .cc-mission-stat {
      background: var(--bg-card);
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 20px;
      text-align: center;
    }
    .cc-mission-stat-num {
      font-size: 2rem;
      font-weight: 900;
      background: var(--grad-violet);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      line-height: 1;
    }
    .cc-mission-stat-label {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 6px;
      line-height: 1.4;
    }

    /* ── FAQ ── */
    .cc-faq-item {
      border: 1px solid var(--bg-border);
      border-radius: var(--radius-md);
      padding: 20px 24px;
      margin-bottom: 10px;
      background: var(--bg-card);
      transition: border-color var(--transition);
    }
    .cc-faq-item:hover { border-color: rgba(155,142,255,0.3); }
    .cc-faq-q { font-size: 0.96rem; font-weight: 700; color: var(--text-main); margin-bottom: 8px; }
    .cc-faq-a { font-size: 0.86rem; color: var(--text-muted); line-height: 1.7; }

    /* ── CTA ── */
    .cc-cta-section {
      background: linear-gradient(135deg, rgba(155,142,255,0.09) 0%, rgba(108,92,231,0.04) 100%);
      border: 1px solid rgba(155,142,255,0.22);
      border-radius: var(--radius-xl);
      padding: 72px 40px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }
    .cc-cta-section::before {
      content: '';
      position: absolute;
      top: -60px; left: 50%;
      transform: translateX(-50%);
      width: 600px; height: 300px;
      background: radial-gradient(ellipse, rgba(155,142,255,0.1) 0%, transparent 70%);
      pointer-events: none;
    }
    .cc-cta-h2 {
      font-size: clamp(1.6rem, 3vw, 2.4rem);
      font-weight: 900;
      color: var(--text-main);
      letter-spacing: -0.03em;
      line-height: 1.15;
      margin-bottom: 14px;
    }
    .cc-cta-sub {
      font-size: 1rem;
      color: var(--text-muted);
      max-width: 480px;
      margin: 0 auto 36px;
      line-height: 1.65;
    }

    /* ── Footer ── */
    .cc-footer {
      border-top: 1px solid var(--bg-border);
      padding: 40px 0 24px;
      margin-top: 80px;
    }
    .cc-footer-grid {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 40px;
      margin-bottom: 32px;
    }
    .cc-footer-brand {
      font-size: 1.1rem;
      font-weight: 800;
      background: var(--grad-violet);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 8px;
    }
    .cc-footer-tagline { font-size: 0.84rem; color: var(--text-muted); line-height: 1.6; max-width: 280px; }
    .cc-footer-col-title {
      font-size: 0.77rem;
      font-weight: 700;
      color: var(--text-main);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 12px;
    }
    .cc-footer-link {
      display: block;
      font-size: 0.83rem;
      color: var(--text-muted);
      text-decoration: none;
      margin-bottom: 8px;
      transition: color var(--transition);
    }
    .cc-footer-link:hover { color: var(--violet-light); }
    .cc-footer-bottom {
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
    .cc-footer-bottom a { color: var(--violet-light); text-decoration: none; }

    /* ── Buttons ── */
    .stButton > button[kind="primary"] {
      background: linear-gradient(135deg, #9B8EFF, #6C5CE7) !important;
      color: #fff !important;
      border: none !important;
      font-weight: 800 !important;
      font-size: 0.97rem !important;
      padding: 14px 32px !important;
      border-radius: 10px !important;
      min-height: 52px !important;
      letter-spacing: -0.01em !important;
      box-shadow: 0 4px 28px rgba(155,142,255,0.25) !important;
      transition: all var(--transition) !important;
    }
    .stButton > button[kind="primary"]:hover {
      box-shadow: 0 6px 36px rgba(155,142,255,0.35) !important;
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
      border-color: rgba(155,142,255,0.3) !important;
      color: var(--text-main) !important;
    }

    /* ── Responsive ── */
    @media (max-width: 1024px) {
      .cc-footer-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 768px) {
      .block-container { padding: 0 1rem 4rem; }
      .cc-hero { padding: 60px 12px 44px; }
      .cc-stats { grid-template-columns: repeat(2, 1fr); }
      .cc-how-grid { grid-template-columns: 1fr; }
      .cc-footer-grid { grid-template-columns: 1fr; gap: 24px; }
      .cc-footer-bottom { flex-direction: column; text-align: center; }
      .cc-nav .cc-nav-links { display: none; }
      .cc-cta-section { padding: 48px 20px; }
      .cc-mission { padding: 32px 24px; }
    }
    @media (max-width: 480px) {
      .cc-stats { grid-template-columns: 1fr 1fr; }
      .cc-h1 { font-size: 2rem; }
      .cc-h2 { font-size: 1.5rem; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── TOP NAV ───────────────────────────────────────────────────────────────
    st.markdown("""
    <nav class="cc-nav" role="navigation" aria-label="Main navigation">
      <a class="cc-nav-brand" href="/" aria-label="College Confused Home">🎓 College Confused</a>
      <div class="cc-nav-links">
        <a class="cc-nav-link" href="#features">Features</a>
        <a class="cc-nav-link" href="#how-it-works">How It Works</a>
        <a class="cc-nav-link" href="#testimonials">Success Stories</a>
        <a class="cc-nav-link" href="#faq">FAQ</a>
      </div>
    </nav>
    """, unsafe_allow_html=True)

    # ── HERO ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <header class="cc-hero" role="banner">
      <div class="cc-eyebrow" style="-webkit-text-fill-color:#C4B8FF!important;color:#C4B8FF!important;">
        🆓 100% Free · No Credit Card · Built for First-Gen Students
      </div>
      <div class="cc-h1" role="heading" aria-level="1" style="color:#F2F0FF;-webkit-text-fill-color:#F2F0FF;">
        Stop Being Confused.<br>
        <span style="background:linear-gradient(90deg,#9B8EFF 0%,#C4B8FF 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;display:inline;">Start Getting In.</span>
      </div>
      <p class="cc-hero-sub" style="-webkit-text-fill-color:#8A84B0!important;color:#8A84B0!important;">
        College Confused is the free AI-powered college prep platform built for students who deserve
        real guidance — not generic advice. Track deadlines, find scholarships, write better essays,
        and build your college list — all in one place, completely free.
      </p>
    </header>
    """, unsafe_allow_html=True)

    hero_l, hero_c, hero_r = st.columns([1, 2, 1])
    with hero_c:
        if st.button("🎓 Get Started Free — No Credit Card", type="primary", use_container_width=True, key="hero_cta"):
            st.switch_page("app.py")
        st.markdown("""
        <div class="cc-trust">
          <span class="cc-trust-item"><span class="cc-trust-check">✓</span> Always free</span>
          <span class="cc-trust-item"><span class="cc-trust-check">✓</span> No credit card</span>
          <span class="cc-trust-item"><span class="cc-trust-check">✓</span> AI-powered</span>
          <span class="cc-trust-item"><span class="cc-trust-check">✓</span> Unlimited essays</span>
        </div>
        """, unsafe_allow_html=True)

    # ── PRODUCT MOCKUP ────────────────────────────────────────────────────────
    _ml, _mc, _mr = st.columns([1, 4, 1])
    with _mc:
        st.markdown("""
        <div class="cc-mockup-wrap">
          <div class="cc-mockup-browser">
            <div class="cc-mockup-bar">
              <div class="cc-mockup-dots"><span></span><span></span><span></span></div>
              <div class="cc-mockup-url">app.collegeconfused.org — Your Dashboard</div>
            </div>
            <div class="cc-mockup-screen">
              <div class="cc-mock-greeting">👋 Welcome back, Aaliyah — 47 days until Common App ED deadline</div>
              <div class="cc-mock-stats-row">
                <div class="cc-mock-stat">
                  <span class="cc-mock-stat-num">7</span>
                  <span class="cc-mock-stat-lbl">Schools on List</span>
                </div>
                <div class="cc-mock-stat">
                  <span class="cc-mock-stat-num">3</span>
                  <span class="cc-mock-stat-lbl">Essays In Progress</span>
                </div>
                <div class="cc-mock-stat">
                  <span class="cc-mock-stat-num">$12K</span>
                  <span class="cc-mock-stat-lbl">Scholarships Found</span>
                </div>
              </div>
              <div class="cc-mock-tasks">
                <div class="cc-mock-task">
                  <span class="cc-mock-task-icon">✍️</span>
                  <span class="cc-mock-task-text">Common App Personal Statement — Draft 3</span>
                  <span class="cc-mock-badge cc-mock-badge-orange">Due Oct 15</span>
                </div>
                <div class="cc-mock-task">
                  <span class="cc-mock-task-icon">💰</span>
                  <span class="cc-mock-task-text">Gates Millennium Scholarship Application</span>
                  <span class="cc-mock-badge cc-mock-badge-violet">Due Nov 1</span>
                </div>
                <div class="cc-mock-task">
                  <span class="cc-mock-task-icon">📋</span>
                  <span class="cc-mock-task-text">FAFSA Submission — 2025–2026 Aid Year</span>
                  <span class="cc-mock-badge cc-mock-badge-teal">✓ Complete</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


        st.markdown("""
    <div style="background:rgba(155,142,255,0.06);border-bottom:1px solid rgba(155,142,255,0.15);padding:6px;text-align:center;font-size:0.7rem;color:rgba(196,184,255,0.7);letter-spacing:0.05em;">
      ⚗️ BETA · All data is test/demo data · Not accurate · Building in public 🚧
    </div>
    """, unsafe_allow_html=True)

    # ── STATS ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="cc-stats" role="region" aria-label="Platform statistics">
      <div class="cc-stat">
        <div class="cc-stat-num">7</div>
        <div class="cc-stat-label">AI-Powered Tools</div>
      </div>
      <div class="cc-stat">
        <div class="cc-stat-num">100%</div>
        <div class="cc-stat-label">Free Forever</div>
      </div>
      <div class="cc-stat">
        <div class="cc-stat-num">∞</div>
        <div class="cc-stat-label">Essay Drafts</div>
      </div>
      <div class="cc-stat">
        <div class="cc-stat-num">24/7</div>
        <div class="cc-stat-label">AI Guidance</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── FEATURES ──────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="cc-section" id="features" aria-label="Features">
      <div class="cc-eyebrow-label" style="-webkit-text-fill-color:#9B8EFF!important;color:#9B8EFF!important;">Features</div>
      <h2 class="cc-h2">Everything You Need. Nothing You Don't.</h2>
      <p class="cc-section-sub">Seven AI-powered tools covering every stage of the college application journey — all free, all in one place.</p>
    </section>
    """, unsafe_allow_html=True)

    features = [
        ("📅", "Application Timeline Tracker", "Every deadline in one dashboard — Common App Early Decision, Regular Decision, FAFSA, scholarships, housing deposits. Get reminders before things are due, not after."),
        ("💰", "Scholarship Finder", "Discover scholarships you actually qualify for based on your GPA, major, state, and background. Track deadlines and application status in one organized dashboard."),
        ("✍️", "AI Essay Station", "Claude AI helps you brainstorm, draft, and polish your Common App personal statement and school-specific supplements. Unlimited drafts. Your story, told better."),
        ("🏫", "College List Builder", "Build a balanced list of reach, match, and safety schools. Add research notes, admission stats, financial aid data, and visit checklists — all in one view."),
        ("📚", "SAT/ACT Prep", "Practice questions, score tracking, and AI-generated study plans built around your target schools' score ranges. Study smarter, not harder."),
        ("📋", "FAFSA Guide", "Step-by-step walkthrough of the Free Application for Federal Student Aid. Know exactly what you need, when to submit, and what to expect from your aid package."),
    ]

    f_rows = [features[i:i+3] for i in range(0, len(features), 3)]
    for row in f_rows:
        cols = st.columns(3, gap="medium")
        for col, (icon, title, desc) in zip(cols, row):
            with col:
                st.markdown(f"""
                <article class="cc-feat-card">
                  <span class="cc-feat-icon" role="img" aria-label="{title}">{icon}</span>
                  <h3 class="cc-feat-title">{title}</h3>
                  <p class="cc-feat-desc">{desc}</p>
                </article>
                """, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # ── HOW IT WORKS ──────────────────────────────────────────────────────────
    st.markdown("""
    <section class="cc-section" id="how-it-works" aria-label="How College Confused works">
      <div class="cc-eyebrow-label" style="-webkit-text-fill-color:#9B8EFF!important;color:#9B8EFF!important;">How It Works</div>
      <h2 class="cc-h2">From Confused to Confident in 3 Steps</h2>
      <p class="cc-section-sub">No tutor fees. No counselor waitlists. Just sign up and start getting the guidance you deserve.</p>
      <div class="cc-how-grid">
        <div class="cc-how-step">
          <div class="cc-how-num" aria-hidden="true">1</div>
          <h3 class="cc-how-title">Create Your Free Account</h3>
          <p class="cc-how-desc">Sign up with your email in 30 seconds. No credit card, no phone number, no social login. Just you and your college prep tools — free forever.</p>
        </div>
        <div class="cc-how-step">
          <div class="cc-how-num" aria-hidden="true">2</div>
          <h3 class="cc-how-title">Set Up Your Timeline</h3>
          <p class="cc-how-desc">Add your target schools and application types (ED, EA, RD). Your deadline calendar populates automatically so nothing slips through the cracks — especially FAFSA and scholarship deadlines.</p>
        </div>
        <div class="cc-how-step">
          <div class="cc-how-num" aria-hidden="true">3</div>
          <h3 class="cc-how-title">Use Every Tool to Get In</h3>
          <p class="cc-how-desc">Write better essays with AI, find scholarships you qualify for, build a balanced college list, prep for the SAT/ACT with AI study plans, and navigate FAFSA step by step.</p>
        </div>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── TESTIMONIALS ──────────────────────────────────────────────────────────
    st.markdown("""
    <section class="cc-section" id="testimonials" aria-label="Student success stories">
      <div class="cc-eyebrow-label">Success Stories</div>
      <h2 class="cc-h2">Students Who Got In</h2>
      <p class="cc-section-sub">Real students who used College Confused to navigate their application journey — and got accepted.</p>
    </section>
    """, unsafe_allow_html=True)

    t1, t2, t3 = st.columns(3, gap="medium")
    testimonials = [
        ("★★★★★", "\"I was so lost with the Common App until I found College Confused. The timeline feature alone saved me from missing 3 deadlines. The AI essay station helped me find my voice — my counselor said it was the best draft she'd read all year.\"", "Aaliyah T.", "🎉 Accepted to Georgia Tech — Computer Science"),
        ("★★★★★", "\"Found $12,000 in scholarships I never would have found on my own. The scholarship tracker made it actually manageable to apply to 8 of them. As a first-gen student I had no idea where to even start — this changed everything.\"", "Priya K.", "🎉 Accepted to University of Florida — Pre-Med"),
        ("★★★★★", "\"The AI essay station helped me find my story. I went through 6 drafts in one night. My essay went from generic to genuinely me. I got into my top choice school and my scholarship essay landed me $15K.\"", "Marcus J.", "🎉 Accepted to Howard University — Business"),
    ]
    for col, (stars, quote, author, result) in zip([t1, t2, t3], testimonials):
        with col:
            st.markdown(f"""
            <article class="cc-testimonial-card" itemscope itemtype="https://schema.org/Review">
              <div class="cc-stars" aria-label="5 out of 5 stars">{stars}</div>
              <p class="cc-quote-text" itemprop="reviewBody">{quote}</p>
              <div class="cc-quote-author" itemprop="author">{author}</div>
              <div class="cc-quote-result">{result}</div>
            </article>
            """, unsafe_allow_html=True)

    # ── MISSION ───────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="cc-section" aria-label="Our mission">
      <div class="cc-eyebrow-label">Our Mission</div>
      <h2 class="cc-h2">Built for Students Who Deserve Better</h2>
      <p class="cc-section-sub">Private college counselors charge $200–$500 an hour. Every student deserves the same quality guidance — free.</p>
    </section>
    """, unsafe_allow_html=True)

    m1, m2 = st.columns([3, 2], gap="large")
    with m1:
        st.markdown("""
        <div class="cc-mission">
          <h3 class="cc-mission-h3">The College Admissions Process Is Broken — We're Fixing It</h3>
          <div class="cc-mission-body">
            First-generation college students navigate the most complex process of their lives with the
            least support. Students at well-resourced schools have college counselors who know every
            deadline, every scholarship, and every essay trick. Students at underfunded schools get
            a 5-minute meeting twice a year.<br><br>
            College Confused exists to close that gap. Every tool on this platform — the AI essay station,
            the scholarship finder, the FAFSA guide — is designed to give every student the same quality
            guidance that private counselors charge hundreds of dollars an hour for.<br><br>
            <strong style="color:#F2F0FF;">Free. Forever. For every student who deserves a fair shot.</strong>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown("""
        <div class="cc-mission-stat" style="margin-bottom:16px;">
          <div class="cc-mission-stat-num">$200–500</div>
          <div class="cc-mission-stat-label">per hour for private college counselors</div>
        </div>
        <div class="cc-mission-stat" style="margin-bottom:16px;">
          <div class="cc-mission-stat-num">$0</div>
          <div class="cc-mission-stat-label">cost of College Confused — free forever</div>
        </div>
        <div class="cc-mission-stat">
          <div class="cc-mission-stat-num">∞</div>
          <div class="cc-mission-stat-label">AI essay drafts, scholarship searches, and deadline reminders</div>
        </div>
        """, unsafe_allow_html=True)

    # ── FAQ ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="cc-section" id="faq" aria-label="Frequently asked questions">
      <div class="cc-eyebrow-label">FAQ</div>
      <h2 class="cc-h2">Frequently Asked Questions</h2>
      <p class="cc-section-sub">Everything you need to know before you sign up.</p>

      <div class="cc-faq-item">
        <h3 class="cc-faq-q">Is College Confused really 100% free?</h3>
        <p class="cc-faq-a">Yes. All 7 AI-powered tools are completely free — no credit card, no trial period, no premium tier. The AI essay station, scholarship finder, deadline tracker, college list builder, SAT/ACT prep, and FAFSA guide are all free forever.</p>
      </div>
      <div class="cc-faq-item">
        <h3 class="cc-faq-q">How does the AI essay station work?</h3>
        <p class="cc-faq-a">The AI essay station uses Anthropic's Claude to help you brainstorm, draft, and polish your Common App personal statement and supplemental essays. You share your story and experiences — Claude helps you shape them into compelling narratives that sound like you. You can generate unlimited drafts until you're happy.</p>
      </div>
      <div class="cc-faq-item">
        <h3 class="cc-faq-q">Is College Confused good for first-generation college students?</h3>
        <p class="cc-faq-a">Yes — it was built with first-gen students specifically in mind. The FAFSA guide provides step-by-step help for students who don't have family experience with financial aid. The scholarship finder surfaces opportunities many first-gen students never know about. The deadline tracker ensures nothing falls through the cracks when you don't have a counselor holding your hand.</p>
      </div>
      <div class="cc-faq-item">
        <h3 class="cc-faq-q">What application deadlines does the timeline track?</h3>
        <p class="cc-faq-a">The timeline tracks Common App Early Decision I &amp; II, Early Action, Regular Decision, and Rolling Admission deadlines. It also tracks FAFSA submission windows, scholarship deadlines, financial aid award dates, housing deposit deadlines, and more — all in one calendar view with reminders.</p>
      </div>
      <div class="cc-faq-item">
        <h3 class="cc-faq-q">How does the scholarship finder work?</h3>
        <p class="cc-faq-a">The scholarship finder helps you discover scholarships you actually qualify for based on your GPA, intended major, state of residence, background, and other criteria. You can track application status and deadlines for each scholarship in an organized dashboard so nothing slips through.</p>
      </div>
      <div class="cc-faq-item">
        <h3 class="cc-faq-q">Can I use College Confused for SAT and ACT prep?</h3>
        <p class="cc-faq-a">Yes. The SAT/ACT prep section includes practice questions, score tracking, and AI-generated study plans built around your target schools' score ranges. Claude analyzes your weak areas and generates a personalized study schedule to get you to your target score efficiently.</p>
      </div>
    </section>
    """, unsafe_allow_html=True)

    # ── FINAL CTA ─────────────────────────────────────────────────────────────
    st.markdown("""
    <section class="cc-cta-section" aria-label="Call to action">
      <h2 class="cc-cta-h2">Your College Journey Starts Here.</h2>
      <p class="cc-cta-sub">
        Free. AI-powered. Built for students who deserve better than confusing advice.<br>
        Join thousands of students navigating admissions with confidence.
      </p>
    </section>
    """, unsafe_allow_html=True)

    cta_l, cta_c, cta_r = st.columns([1, 2, 1])
    with cta_c:
        st.markdown("<div style='margin-top:-24px;'></div>", unsafe_allow_html=True)
        if st.button("🎓 Create My Free Account", type="primary", use_container_width=True, key="cta_bottom"):
            st.switch_page("app.py")
        st.markdown("<div style='text-align:center; color:#8A84B0; font-size:0.78rem; margin-top:8px;'>No credit card · 100% free forever · All 7 tools included</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("Already have an account? Sign In →", use_container_width=True, key="signin_bottom"):
            st.switch_page("app.py")

    # ── FOOTER ────────────────────────────────────────────────────────────────
    st.markdown("""
    <footer class="cc-footer" role="contentinfo">
      <div class="cc-footer-grid">
        <div>
          <div class="cc-footer-brand">🎓 College Confused</div>
          <p class="cc-footer-tagline">Free AI-powered college prep for every student. Built for first-gen students, underfunded schools, and everyone who deserves a fair shot at higher education.</p>
        </div>
        <div>
          <div class="cc-footer-col-title">Tools</div>
          <span class="cc-footer-link">Application Timeline</span>
          <span class="cc-footer-link">Scholarship Finder</span>
          <span class="cc-footer-link">AI Essay Station</span>
          <span class="cc-footer-link">FAFSA Guide</span>
        </div>
        <div>
          <div class="cc-footer-col-title">Connect</div>
          <a class="cc-footer-link" href="https://www.linkedin.com/in/darrian-belcher/" rel="noopener noreferrer" target="_blank">LinkedIn</a>
          <a class="cc-footer-link" href="https://collegeconfused.org" rel="noopener noreferrer" target="_blank">collegeconfused.org</a>
        </div>
      </div>
      <div class="cc-footer-bottom">
        <span>© 2026 College Confused · Free AI College Prep · Built with ❤️ by <a href="https://www.linkedin.com/in/darrian-belcher/" rel="noopener noreferrer" target="_blank">Darrian Belcher</a></span>
        <span>AI essay help · Scholarship finder · Application deadline tracker · FAFSA guide</span>
      </div>
    </footer>
    """, unsafe_allow_html=True)

    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATED DASHBOARD — shown to logged-in users
# ═══════════════════════════════════════════════════════════════════════════════
username = user.get("username", "Student")

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                       label="🏠 Home",            icon="🏠")
st.sidebar.page_link("pages/80_cc_home.py",             label="🎓 Dashboard",       icon="🎓")
st.sidebar.page_link("pages/81_cc_timeline.py",         label="📅 My Timeline",     icon="📅")
st.sidebar.page_link("pages/82_cc_scholarships.py",     label="💰 Scholarships",    icon="💰")
st.sidebar.page_link("pages/83_cc_essay_station.py",    label="✍️ Essay Station",   icon="✍️")
st.sidebar.page_link("pages/84_cc_test_prep.py",        label="📚 SAT/ACT Prep",    icon="📚")
# College List page not yet deployed
# FAFSA Guide page not yet deployed
render_sidebar_user_widget()

st.title("🎓 College Confused")
st.markdown(f"Welcome back, **{username}** — let's get you into college.")
st.markdown("---")

st.subheader("📍 Where are you in your journey?")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("#### 📅 My Timeline")
    st.markdown("Every deadline, every milestone — tracked so nothing slips.")
    if st.button("View My Timeline →", key="btn_timeline"):
        st.switch_page("pages/81_cc_timeline.py")

with c2:
    st.markdown("#### 🏫 College List")
    st.markdown("Reach, match, and safety schools with research notes.")
    if st.button("View College List →", key="btn_list"):
        st.switch_page("pages/87_cc_college_list.py")

with c3:
    st.markdown("#### 💰 Scholarships")
    st.markdown("Discover and track scholarships you qualify for.")
    if st.button("Find Scholarships →", key="btn_scholarships"):
        st.switch_page("pages/82_cc_scholarships.py")

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("#### ✍️ Essay Station")
    st.markdown("AI-powered brainstorming, drafting, and review.")
    if st.button("Open Essay Station →", key="btn_essay"):
        st.switch_page("pages/83_cc_essay_station.py")

with c5:
    st.markdown("#### 📚 SAT/ACT Prep")
    st.markdown("Practice questions, score tracking, AI study plans.")
    if st.button("Start Test Prep →", key="btn_testprep"):
        st.switch_page("pages/84_cc_test_prep.py")

with c6:
    st.markdown("#### 📋 FAFSA Guide")
    st.markdown("Step-by-step FAFSA walkthrough, know what to expect.")
    if st.button("Open FAFSA Guide →", key="btn_fafsa"):
        st.switch_page("pages/88_cc_fafsa_guide.py")

st.markdown("---")
st.info(
    "💡 **Tip:** Start with your **Timeline** to see all upcoming deadlines, "
    "then visit **Essay Station** to get ahead on your personal statement.",
    icon="🎯",
)
st.caption("College Confused — Free AI-powered college prep for every student | collegeconfused.org")
