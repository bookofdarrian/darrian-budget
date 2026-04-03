# AI Ethics Business Requirements Document (BRD)
## C2C Referral Flywheel (Students + Resellers)

**Owner:** Darrian Belcher  
**Date:** 2026-04-01  
**Priority:** High

---

## PART 1 — FEATURE OVERVIEW

| Field | Value |
|---|---|
| Feature Name | C2C Referral Flywheel |
| Page / Module | Referral links, reward ledger, anti-abuse checks, invite analytics |
| Affected Products | College Confused (students), SoleOps (resellers) |

### Problem Statement
Growth is heavily content-driven today. A structured peer referral loop can compound acquisition and retention at lower marginal cost.

---

## PART 2 — RESEARCH + ETHICS

### Primary Sources
1. Schmitt, P., Skiera, B., & Van den Bulte, C. (2011). Referral Programs and Customer Value. *Journal of Marketing, 75*(1), 46–59.  
2. Villanueva, J., Yoo, S., & Hanssens, D. M. (2008). Impact of Marketing-Induced vs Word-of-Mouth Acquisition. *Journal of Marketing Research, 45*(1), 48–59.

### Risks & Mitigations
- Fraud/abuse (score 4): anti-self-referral and velocity limits.
- Equity/access (score 3): ensure non-monetary reward paths for low-income users.
- Community impact (score 2): rewards designed to support learning/business growth, not extraction.

**Community Sovereignty Test:**
- [x] ✅ PASS

---

## PART 3 — REQUIREMENTS

- Unique referral links per user.
- Reward rules:
  - CC: scholarship prep credits, premium coaching minutes.
  - SoleOps: free Pro trial days, feature credits.
- Abuse protections: IP/device velocity checks, cool-down window, manual review queue.
- Referral analytics: invites sent, activation rate, retained referrals (30-day).

---

## PART 4 — MONETARY IMPACT

| Metric | Estimate |
|---|---:|
| CAC reduction target | 15–35% |
| Referral-attributed signups target | 20–40% of new users |
| Retention uplift target | 5–15% |

---

## PART 5 — CHECKLIST

- [ ] Referral table schema + reward ledger
- [ ] Invite link generation and tracking
- [ ] Anti-abuse rules and review queue
- [ ] KPI dashboard for referral performance
