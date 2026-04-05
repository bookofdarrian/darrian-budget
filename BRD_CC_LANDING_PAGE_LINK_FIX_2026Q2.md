ce# BRD: College Confused Landing Page Link Fix

**Date:** 2026-04-05
**Author:** Darrian Belcher (AI-assisted)
**Priority:** P0 — Critical (landing page broken for all visitors)
**Branch:** `hotfix/cc-landing-page-links`

---

## Problem Statement

The College Confused landing page at `collegeconfused.org` has two critical issues:

### Issue 1: Stale Entry Point
- The systemd service runs `app.py` but the deploy script (`deploy_college_confused.sh`) only rsyncs `pages/` and `utils/`
- It **never copies `cc_app.py` → `app.py`** in the serving directory
- Result: The landing page served to visitors is from March 22 (stale), not the latest version

### Issue 2: Broken Footer Navigation Links
- Footer links use raw HTML `<a href="/cc_timeline">` etc.
- These paths don't work in Streamlit — they cause full page reloads to non-existent routes
- Correct approach: Use `st.switch_page()` for navigation, or use Streamlit-compatible paths

### Issue 3: CTA Buttons Navigate to Login, Not Signup
- "Get Started Free" and "Create My Free Account" buttons use `st.switch_page("pages/80_cc_home.py")`
- This goes to the dashboard which requires login — confusing for new visitors
- Should link to a signup/registration flow or at minimum show the login page

---

## Research & Impact

### Sources
1. Streamlit Multipage App Documentation (2024) — `st.switch_page()` is the only reliable way to navigate between pages in a Streamlit multipage app. Raw HTML `<a href>` links bypass Streamlit's routing.
2. Nielsen Norman Group, "Landing Page Best Practices" (2023) — CTAs on landing pages must link directly to the conversion action (signup/login). Broken navigation causes 40-60% bounce rate increase.

### Monetary Impact
- **collegeconfused.org** is a nonprofit platform targeting first-gen students
- Every broken link = a student who bounces and never comes back
- With SEO driving organic traffic, broken landing page links waste all SEO investment

### Community Sovereignty Test
✅ **PASS** — This fix empowers students by ensuring they can actually access the free tools advertised on the landing page. No extraction.

---

## Solution

### Fix 1: Update Deploy Script
Add `cc_app.py → app.py` copy to `deploy_college_confused.sh`:
```bash
ssh "$SERVER" "cp $CC_SOURCE/cc_app.py $CC_SERVE/app.py"
```

### Fix 2: Fix Footer Links
Replace raw HTML `<a href>` footer links with JavaScript that triggers Streamlit page navigation, or convert them to `st.button` / `st.page_link` calls.

Since footer links are in a `st.markdown()` block (HTML), the best approach is to use Streamlit-compatible URL paths that work with the multipage router:
- `/cc_home` → `pages/80_cc_home.py`
- `/cc_timeline` → `pages/81_cc_timeline.py`
- etc.

### Fix 3: Copy cc_global_css.py to serving dir
The deploy script also doesn't copy `cc_app.py` or `cc_global_css.py` — both are root-level files needed by CC.

---

## Ethical Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Student data exposure | None | No data changes, only navigation fix |
| Accessibility regression | Low | Footer links remain keyboard-navigable |
| SEO impact | Positive | Working links improve crawlability |

---

## Acceptance Criteria
- [ ] `deploy_college_confused.sh` copies `cc_app.py → app.py` and `cc_global_css.py`
- [ ] Footer links navigate correctly to CC tool pages
- [ ] CTA buttons ("Get Started Free") work for unauthenticated users
- [ ] All CC pages load correctly at collegeconfused.org
- [ ] Deployed and verified on prod
