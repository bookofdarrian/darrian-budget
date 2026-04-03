# BRD: CC db_exec() Migration + 4-Hour Autonomous Agent Sprint Plan
**Date:** 2026-04-03 | **Author:** Darrian Belcher | **Status:** APPROVED

---

## 1. Problem Statement

Two CC pages (`pages/94_cc_recommendation_letter_tracker.py` and `pages/95_cc_interview_prep_ai.py`) use raw `cur.execute()` instead of the project-standard `db_exec()` wrapper. This bypasses query logging, PostgreSQL compatibility shims, and the pre-commit safety net. Additionally, Darrian is driving 8 hours VA-bound and needs a structured autonomous agent plan to execute ~4 hours of productive SDLC work unattended.

## 2. Scope

### 2a. Code Fix (This Commit)
| File | Change |
|------|--------|
| `pages/94_cc_recommendation_letter_tracker.py` | All 14 `cur.execute()` → `db_exec()` |
| `pages/95_cc_interview_prep_ai.py` | All 10 `cur.execute()` → `db_exec()` |

### 2b. Autonomous Agent Sprint Plan (4 Hours)
| Hour | Task | Branch | SDLC Gate |
|------|------|--------|-----------|
| 1 | CC Contrast Fix — WCAG AA compliance | `feature/cc-wcag-contrast-fix` | py_compile + tests + merge to dev |
| 2 | Accessibility Theme Settings — page 142 | `feature/accessibility-theme-settings` | py_compile + tests + merge to dev |
| 3 | SoleOps User Registration Flow polish | `feature/soleops-user-reg-polish` | py_compile + tests + merge to dev |
| 4 | CC pages 85-86 stubs + backlog cleanup | `feature/cc-missing-pages-stubs` | py_compile + tests + merge to dev |

## 3. Success Criteria
- [x] Zero `cur.execute()` or `conn.execute()` in pages 94 and 95
- [x] All CC unit tests pass (49/49)
- [x] Both files pass `py_compile`
- [ ] Agent plan executes 4 hours of work autonomously
- [ ] Each agent task follows SDLC: feature branch → tests → dev → qa → staging → main

## 4. Backlog Updates (Added This Sprint)
1. **CC: WCAG AA Contrast Fix** — Replace `--text-muted: #8A84B0` with `#B0ACCC`, enforce 4.5:1 ratio
2. **Accessibility Theme Settings** — page 142 — User theme picker for all 3 sites
3. **SoleOps User Registration Flow** — Email/password + Stripe checkout
4. **CC: Missing pages 85-86** — Stub pages for future features
5. **collegeconfused.org deployment** — Retry when Tailscale is up

## 5. Ethical Review
- ✅ No user data affected
- ✅ No new data collection
- ✅ Community sovereignty maintained
- ✅ All changes improve code quality and accessibility

## 6. Risk Assessment
| Risk | Mitigation |
|------|-----------|
| Agent runs without human review | Each task has automated test gates; no merge to main without passing |
| Server unreachable for CC deploy | Queued for next Tailscale connection |
| db_exec() signature mismatch | Verified against utils/db.py — `execute(conn, sql, params=None)` returns cursor |
